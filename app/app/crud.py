from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics import DATABASE_DURATION, DATABASE_OPERATIONS
from app.models import Order
from app.schemas import OrderCreate, OrderUpdate
from app.telemetry import current_trace_exemplar


def _observe(operation: str, started_at: float, outcome: str) -> None:
    DATABASE_OPERATIONS.labels(operation, outcome).inc()
    DATABASE_DURATION.labels(operation).observe(
        perf_counter() - started_at,
        exemplar=current_trace_exemplar(),
    )


async def create_order(session: AsyncSession, payload: OrderCreate) -> Order:
    started_at = perf_counter()
    order = Order(**payload.model_dump())
    session.add(order)
    try:
        await session.commit()
        await session.refresh(order)
        _observe("create", started_at, "success")
        return order
    except SQLAlchemyError:
        await session.rollback()
        _observe("create", started_at, "error")
        raise


async def list_orders(session: AsyncSession, offset: int, limit: int) -> tuple[list[Order], int]:
    started_at = perf_counter()
    try:
        rows = await session.scalars(
            select(Order).order_by(Order.id.desc()).offset(offset).limit(limit)
        )
        total = await session.scalar(select(func.count()).select_from(Order))
        _observe("list", started_at, "success")
        return list(rows), int(total or 0)
    except SQLAlchemyError:
        _observe("list", started_at, "error")
        raise


async def get_order(session: AsyncSession, order_id: int) -> Order | None:
    started_at = perf_counter()
    try:
        order = await session.get(Order, order_id)
        _observe("get", started_at, "success")
        return order
    except SQLAlchemyError:
        _observe("get", started_at, "error")
        raise


async def update_order(session: AsyncSession, order: Order, payload: OrderUpdate) -> Order:
    started_at = perf_counter()
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(order, field, value)
    try:
        await session.commit()
        await session.refresh(order)
        _observe("update", started_at, "success")
        return order
    except SQLAlchemyError:
        await session.rollback()
        _observe("update", started_at, "error")
        raise


async def delete_order(session: AsyncSession, order: Order) -> None:
    started_at = perf_counter()
    try:
        await session.delete(order)
        await session.commit()
        _observe("delete", started_at, "success")
    except SQLAlchemyError:
        await session.rollback()
        _observe("delete", started_at, "error")
        raise
