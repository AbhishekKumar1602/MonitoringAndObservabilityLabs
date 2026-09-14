import logging

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.config import settings
from app.metrics import CACHE_OPERATIONS
from app.schemas import OrderRead
from app.telemetry import get_tracer, record_cache_operation

logger = logging.getLogger(__name__)
_client: redis.Redis | None = None


def get_cache_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            health_check_interval=30,
        )
    return _client


async def check_cache() -> tuple[bool, str]:
    try:
        await get_cache_client().ping()
        return True, "ok"
    except RedisError as exc:
        logger.warning("cache.health_check_failed", extra={"error_type": type(exc).__name__})
        return False, type(exc).__name__


async def get_cached_order(order_id: int) -> OrderRead | None:
    with get_tracer().start_as_current_span("cache.get_order") as span:
        span.set_attribute("db.system", "redis")
        span.set_attribute("order.id", order_id)
        try:
            value = await get_cache_client().get(f"order:{order_id}")
            outcome = "hit" if value is not None else "miss"
            CACHE_OPERATIONS.labels("get", outcome).inc()
            record_cache_operation("get", outcome)
            span.set_attribute("cache.hit", value is not None)
            return OrderRead.model_validate_json(value) if value is not None else None
        except (RedisError, ValueError) as exc:
            CACHE_OPERATIONS.labels("get", "error").inc()
            record_cache_operation("get", "error")
            span.record_exception(exc)
            logger.warning(
                "cache.get_failed",
                extra={"order_id": order_id, "error_type": type(exc).__name__},
            )
            return None


async def set_cached_order(order: OrderRead) -> None:
    try:
        await get_cache_client().set(
            f"order:{order.id}", order.model_dump_json(), ex=settings.cache_ttl_seconds
        )
        CACHE_OPERATIONS.labels("set", "success").inc()
        record_cache_operation("set", "success")
    except RedisError as exc:
        CACHE_OPERATIONS.labels("set", "error").inc()
        record_cache_operation("set", "error")
        logger.warning(
            "cache.set_failed",
            extra={"order_id": order.id, "error_type": type(exc).__name__},
        )


async def delete_cached_order(order_id: int) -> None:
    try:
        await get_cache_client().delete(f"order:{order_id}")
        CACHE_OPERATIONS.labels("delete", "success").inc()
        record_cache_operation("delete", "success")
    except RedisError as exc:
        CACHE_OPERATIONS.labels("delete", "error").inc()
        record_cache_operation("delete", "error")
        logger.warning(
            "cache.delete_failed",
            extra={"order_id": order_id, "error_type": type(exc).__name__},
        )


async def close_cache() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
