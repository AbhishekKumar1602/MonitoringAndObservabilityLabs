import logging
import socket
from dataclasses import dataclass
from decimal import Decimal

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.config import settings
from app.database import engine
from app.logging_config import JsonFormatter

logger = logging.getLogger(__name__)


@dataclass
class TelemetryProviders:
    tracer_provider: TracerProvider
    meter_provider: MeterProvider
    logger_provider: LoggerProvider


_providers: TelemetryProviders | None = None
_orders_created_counter = None
_order_value_histogram = None
_cache_operation_counter = None
_simulation_counter = None


class _ExcludeTelemetryInternals(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith(("opentelemetry", "grpc"))


def configure_telemetry(app: FastAPI) -> TelemetryProviders | None:
    """Configure OTLP traces, metrics, and logs plus supported auto-instrumentation."""

    global _providers
    global _orders_created_counter
    global _order_value_histogram
    global _cache_operation_counter
    global _simulation_counter

    if not settings.otel_enabled:
        logger.warning("telemetry.disabled")
        return None
    if _providers is not None:
        return _providers

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.namespace": "observability-labs",
            "service.version": settings.version,
            "service.instance.id": socket.gethostname(),
            "deployment.environment.name": settings.environment,
            "vcs.ref.head.revision": settings.build_sha,
        }
    )

    tracer_provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(settings.otel_trace_sample_ratio)),
    )
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=settings.otel_exporter_otlp_insecure,
            )
        )
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=settings.otel_exporter_otlp_insecure,
        ),
        export_interval_millis=settings.otel_metric_export_interval_ms,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=settings.otel_exporter_otlp_insecure,
            )
        )
    )
    set_logger_provider(logger_provider)
    otel_log_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    otel_log_handler.setFormatter(JsonFormatter())
    otel_log_handler.addFilter(_ExcludeTelemetryInternals())
    logging.getLogger().addHandler(otel_log_handler)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        excluded_urls="/metrics,/health/live",
    )
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=tracer_provider)
    RedisInstrumentor().instrument(tracer_provider=tracer_provider)
    HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)

    meter = metrics.get_meter("observability_labs.orders", settings.version)
    _orders_created_counter = meter.create_counter(
        "orders.created", unit="{order}", description="Orders successfully created."
    )
    _order_value_histogram = meter.create_histogram(
        "orders.value", unit="USD", description="Value of newly created orders."
    )
    _cache_operation_counter = meter.create_counter(
        "cache.operations", unit="{operation}", description="Redis cache operations by outcome."
    )
    _simulation_counter = meter.create_counter(
        "lab.simulations", unit="{simulation}", description="Controlled lab simulations invoked."
    )

    _providers = TelemetryProviders(tracer_provider, meter_provider, logger_provider)
    logger.info(
        "telemetry.configured",
        extra={"otlp_endpoint": settings.otel_exporter_otlp_endpoint},
    )
    return _providers


def get_tracer():
    return trace.get_tracer("observability_labs.orders", settings.version)


def current_trace_exemplar() -> dict[str, str] | None:
    context = trace.get_current_span().get_span_context()
    if not context.is_valid or not context.trace_flags.sampled:
        return None
    return {"trace_id": format(context.trace_id, "032x")}


def record_order_created(status: str, quantity: int, unit_price: Decimal) -> None:
    if _orders_created_counter is not None:
        attributes = {"order.status": status}
        _orders_created_counter.add(1, attributes)
        _order_value_histogram.record(float(unit_price * quantity), attributes)


def record_cache_operation(operation: str, outcome: str) -> None:
    if _cache_operation_counter is not None:
        _cache_operation_counter.add(1, {"cache.operation": operation, "cache.outcome": outcome})


def record_simulation(kind: str, outcome: str) -> None:
    if _simulation_counter is not None:
        _simulation_counter.add(1, {"simulation.kind": kind, "simulation.outcome": outcome})


def shutdown_telemetry() -> None:
    global _providers
    if _providers is None:
        return
    _providers.logger_provider.force_flush(timeout_millis=5_000)
    _providers.tracer_provider.force_flush(timeout_millis=5_000)
    _providers.meter_provider.force_flush(timeout_millis=5_000)
    _providers.logger_provider.shutdown()
    _providers.tracer_provider.shutdown()
    _providers.meter_provider.shutdown()
    _providers = None
