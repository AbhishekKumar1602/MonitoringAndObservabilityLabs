import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api import router
from app.cache import close_cache, get_cache_client
from app.config import settings
from app.database import close_database, initialize_database
from app.logging_config import configure_logging
from app.metrics import initialize_build_info
from app.middleware import RequestObservabilityMiddleware
from app.telemetry import configure_telemetry, shutdown_telemetry

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialize_database()
    try:
        await get_cache_client().ping()
        logger.info("cache.connected")
    except Exception as exc:
        logger.warning("cache.unavailable_at_startup", extra={"error_type": type(exc).__name__})
    initialize_build_info(settings.version, settings.environment, settings.build_sha)
    logger.info(
        "application.started",
        extra={"version": settings.version, "environment": settings.environment},
    )
    yield
    logger.info("application.stopping")
    await close_cache()
    await close_database()
    shutdown_telemetry()


app = FastAPI(
    title=settings.name,
    version=settings.version,
    description=(
        "A deliberately observable CRUD API for progressive Prometheus, Grafana, "
        "Alertmanager, OpenTelemetry, Loki, and Tempo labs."
    ),
    lifespan=lifespan,
)
app.add_middleware(RequestObservabilityMiddleware)
app.include_router(router)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("database.operation_failed", extra={"error_type": type(exc).__name__})
    return JSONResponse(
        status_code=503,
        content={"detail": "Database operation failed", "error_type": type(exc).__name__},
    )


configure_telemetry(app)
