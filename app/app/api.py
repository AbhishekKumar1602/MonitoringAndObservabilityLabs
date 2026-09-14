import asyncio
import logging
import math
import time
from collections import deque
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from opentelemetry.trace import Status, StatusCode
from prometheus_client import REGISTRY
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.cache import (
    check_cache,
    delete_cached_order,
    get_cache_client,
    get_cached_order,
    set_cached_order,
)
from app.config import settings
from app.database import check_database, get_session
from app.metrics import ALERT_WEBHOOKS, ORDERS_CREATED, SIMULATIONS
from app.schemas import OrderCreate, OrderRead, OrderUpdate
from app.telemetry import get_tracer, record_order_created, record_simulation

logger = logging.getLogger(__name__)
router = APIRouter()
alerts_received: deque[dict[str, Any]] = deque(maxlen=100)
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/", tags=["system"])
async def root() -> dict[str, Any]:
    return {
        "service": settings.name,
        "version": settings.version,
        "environment": settings.environment,
        "docs": "/docs",
        "health": {"liveness": "/health/live", "readiness": "/health/ready"},
        "metrics": "/metrics",
    }


@router.get("/health/live", tags=["system"])
@router.get("/health", include_in_schema=False)
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready", tags=["system"])
@router.get("/ready", include_in_schema=False)
async def readiness(response: Response) -> dict[str, Any]:
    (database_ok, database_detail), (cache_ok, cache_detail) = await asyncio.gather(
        check_database(), check_cache()
    )
    ready = database_ok and cache_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "dependencies": {
            "postgresql": {
                "status": "ok" if database_ok else "error",
                "detail": database_detail,
            },
            "redis": {"status": "ok" if cache_ok else "error", "detail": cache_detail},
        },
    }


@router.get("/metrics", tags=["system"], include_in_schema=False)
async def metrics_endpoint() -> Response:
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@router.post(
    "/api/v1/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    tags=["orders"],
)
async def create_order(payload: OrderCreate, session: SessionDependency) -> OrderRead:
    with get_tracer().start_as_current_span("orders.create") as span:
        span.set_attribute("order.product", payload.product)
        span.set_attribute("order.quantity", payload.quantity)
        order = await crud.create_order(session, payload)
        result = OrderRead.model_validate(order)
        await set_cached_order(result)
        ORDERS_CREATED.labels(result.status).inc()
        record_order_created(result.status, result.quantity, result.unit_price)
        span.set_attribute("order.id", result.id)
        logger.info(
            "order.created",
            extra={"order_id": result.id, "order_status": result.status},
        )
        return result


@router.get("/api/v1/orders", response_model=list[OrderRead], tags=["orders"])
async def list_orders(
    response: Response,
    session: SessionDependency,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[OrderRead]:
    orders, total = await crud.list_orders(session, offset=offset, limit=limit)
    response.headers["x-total-count"] = str(total)
    return [OrderRead.model_validate(order) for order in orders]


@router.get("/api/v1/orders/{order_id}", response_model=OrderRead, tags=["orders"])
async def get_order(order_id: int, session: SessionDependency) -> OrderRead:
    with get_tracer().start_as_current_span("orders.get") as span:
        span.set_attribute("order.id", order_id)
        cached = await get_cached_order(order_id)
        if cached is not None:
            span.set_attribute("cache.hit", True)
            return cached

        span.set_attribute("cache.hit", False)
        order = await crud.get_order(session, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        result = OrderRead.model_validate(order)
        await set_cached_order(result)
        return result


@router.put("/api/v1/orders/{order_id}", response_model=OrderRead, tags=["orders"])
async def update_order(
    order_id: int,
    payload: OrderUpdate,
    session: SessionDependency,
) -> OrderRead:
    with get_tracer().start_as_current_span("orders.update") as span:
        span.set_attribute("order.id", order_id)
        order = await crud.get_order(session, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        updated = await crud.update_order(session, order, payload)
        result = OrderRead.model_validate(updated)
        await set_cached_order(result)
        logger.info("order.updated", extra={"order_id": order_id})
        return result


@router.delete("/api/v1/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["orders"])
async def delete_order(order_id: int, session: SessionDependency) -> Response:
    with get_tracer().start_as_current_span("orders.delete") as span:
        span.set_attribute("order.id", order_id)
        order = await crud.get_order(session, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        await crud.delete_order(session, order)
        await delete_cached_order(order_id)
        logger.info("order.deleted", extra={"order_id": order_id})
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/simulate/latency", tags=["simulations"])
async def simulate_latency(seconds: float = Query(default=2.0, ge=0.0, le=15.0)) -> dict[str, Any]:
    if seconds > settings.simulation_max_latency_seconds:
        raise HTTPException(
            status_code=400,
            detail="Requested delay exceeds the configured safety limit",
        )
    with get_tracer().start_as_current_span("simulation.latency") as span:
        span.set_attribute("simulation.latency.seconds", seconds)
        await asyncio.sleep(seconds)
    SIMULATIONS.labels("latency", "success").inc()
    record_simulation("latency", "success")
    logger.warning("simulation.latency_completed", extra={"seconds": seconds})
    return {"simulation": "latency", "slept_seconds": seconds}


@router.get("/api/v1/simulate/error", tags=["simulations"])
async def simulate_error(status_code: int = Query(default=500, ge=400, le=599)) -> None:
    SIMULATIONS.labels("http_error", "expected_error").inc()
    record_simulation("http_error", "expected_error")
    logger.error("simulation.http_error", extra={"simulated_status_code": status_code})
    raise HTTPException(status_code=status_code, detail="Intentional lab error")


@router.get("/api/v1/simulate/exception", tags=["simulations"])
async def simulate_exception() -> None:
    SIMULATIONS.labels("exception", "expected_error").inc()
    record_simulation("exception", "expected_error")
    raise RuntimeError("Intentional unhandled exception for observability labs")


def _burn_cpu(seconds: float) -> int:
    deadline = time.perf_counter() + seconds
    iterations = 0
    value = 0.0
    while time.perf_counter() < deadline:
        value += math.sqrt((iterations % 10_000) + 1)
        iterations += 1
    return iterations + int(value > 0)


@router.get("/api/v1/simulate/cpu", tags=["simulations"])
async def simulate_cpu(seconds: float = Query(default=2.0, ge=0.1, le=10.0)) -> dict[str, Any]:
    if seconds > settings.simulation_max_cpu_seconds:
        raise HTTPException(
            status_code=400,
            detail="Requested burn exceeds the configured safety limit",
        )
    with get_tracer().start_as_current_span("simulation.cpu") as span:
        span.set_attribute("simulation.cpu.seconds", seconds)
        iterations = await asyncio.to_thread(_burn_cpu, seconds)
        span.set_attribute("simulation.cpu.iterations", iterations)
    SIMULATIONS.labels("cpu", "success").inc()
    record_simulation("cpu", "success")
    return {"simulation": "cpu", "seconds": seconds, "iterations": iterations}


@router.get("/api/v1/simulate/memory", tags=["simulations"])
async def simulate_memory(
    megabytes: int = Query(default=32, ge=1, le=128),
    hold_seconds: float = Query(default=3.0, ge=0.0, le=15.0),
) -> dict[str, Any]:
    if megabytes > settings.simulation_max_memory_mb:
        raise HTTPException(status_code=400, detail="Requested allocation exceeds the safety limit")
    with get_tracer().start_as_current_span("simulation.memory") as span:
        span.set_attribute("simulation.memory.megabytes", megabytes)
        allocation = bytearray(megabytes * 1024 * 1024)
        for page_start in range(0, len(allocation), 4096):
            allocation[page_start] = 1
        allocation[-1] = 1
        await asyncio.sleep(hold_seconds)
        del allocation
    SIMULATIONS.labels("memory", "success").inc()
    record_simulation("memory", "success")
    return {
        "simulation": "memory",
        "allocated_megabytes": megabytes,
        "held_seconds": hold_seconds,
    }


@router.get("/api/v1/simulate/database-error", tags=["simulations"])
async def simulate_database_error(
    session: SessionDependency,
) -> None:
    try:
        with get_tracer().start_as_current_span("simulation.database_error"):
            await session.execute(text("SELECT * FROM obslab_intentionally_missing_table"))
    except Exception as exc:
        await session.rollback()
        SIMULATIONS.labels("database_error", "expected_error").inc()
        record_simulation("database_error", "expected_error")
        logger.error(
            "simulation.database_error",
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(status_code=503, detail="Intentional database failure") from exc
    raise HTTPException(status_code=500, detail="The intentional failure did not occur")


@router.get("/api/v1/simulate/cache", tags=["simulations"])
async def simulate_cache(
    key: str = Query(default="demo", min_length=1, max_length=80),
    force_miss: bool = Query(default=False),
) -> dict[str, Any]:
    cache_key = f"simulation:{key}"
    client = get_cache_client()
    if force_miss:
        await client.delete(cache_key)
    value = await client.get(cache_key)
    hit = value is not None
    if not hit:
        value = f"generated-at-{time.time_ns()}"
        await client.set(cache_key, value, ex=settings.cache_ttl_seconds)
    SIMULATIONS.labels("cache", "hit" if hit else "miss").inc()
    record_simulation("cache", "hit" if hit else "miss")
    return {"simulation": "cache", "key": key, "cache_hit": hit, "value": value}


@router.get("/api/v1/simulate/trace", tags=["simulations"])
async def simulate_trace(
    fail_payment: bool = Query(default=False),
) -> dict[str, Any]:
    tracer = get_tracer()
    with tracer.start_as_current_span("checkout.workflow") as checkout_span:
        checkout_span.set_attribute("checkout.currency", "USD")
        with tracer.start_as_current_span("inventory.reserve"):
            await asyncio.sleep(0.08)
        with tracer.start_as_current_span("payment.authorize") as payment_span:
            await asyncio.sleep(0.12)
            if fail_payment:
                payment_span.set_status(Status(StatusCode.ERROR, "simulated decline"))
                payment_span.add_event("payment.declined", {"reason": "lab_simulation"})
                SIMULATIONS.labels("trace", "expected_error").inc()
                record_simulation("trace", "expected_error")
                raise HTTPException(status_code=402, detail="Intentional payment decline")
        with tracer.start_as_current_span("notification.enqueue"):
            await asyncio.sleep(0.03)
    SIMULATIONS.labels("trace", "success").inc()
    record_simulation("trace", "success")
    return {"simulation": "trace", "status": "checkout_complete"}


@router.post("/internal/alertmanager/webhook", include_in_schema=False)
async def receive_alertmanager_webhook(payload: dict[str, Any]) -> dict[str, int]:
    alerts = payload.get("alerts", [])
    for alert in alerts:
        alerts_received.append(alert)
        ALERT_WEBHOOKS.labels(str(alert.get("status", "unknown"))).inc()
    logger.warning(
        "alertmanager.notification_received",
        extra={"notification_status": payload.get("status"), "alert_count": len(alerts)},
    )
    return {"accepted": len(alerts)}


@router.get("/api/v1/lab/alerts", tags=["simulations"])
async def list_received_alerts() -> dict[str, Any]:
    return {"count": len(alerts_received), "alerts": list(alerts_received)}
