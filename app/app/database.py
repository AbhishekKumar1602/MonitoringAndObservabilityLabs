import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_recycle=300,
    connect_args={
        "timeout": settings.database_connect_timeout_seconds,
        "command_timeout": settings.database_command_timeout_seconds,
    },
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def initialize_database(attempts: int = 12, delay_seconds: float = 2.0) -> None:
    """Create the lab schema, retrying while PostgreSQL finishes startup."""

    from app import models  # noqa: F401 - registers ORM metadata

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            logger.info("database.initialized", extra={"attempt": attempt})
            return
        except Exception as exc:  # startup retry is intentionally broad
            last_error = exc
            logger.warning(
                "database.initialization_retry",
                extra={
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "error_type": type(exc).__name__,
                },
            )
            if attempt < attempts:
                await asyncio.sleep(delay_seconds)
    raise RuntimeError(
        "PostgreSQL did not become ready before the startup deadline"
    ) from last_error


async def check_database() -> tuple[bool, str]:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        logger.warning("database.health_check_failed", extra={"error_type": type(exc).__name__})
        return False, type(exc).__name__


async def close_database() -> None:
    await engine.dispose()
