from prometheus_client import Counter, Gauge, Histogram, Info

HTTP_REQUESTS = Counter(
    "obslab_http_requests_total",
    "Total HTTP requests processed by the application.",
    ["method", "route", "status_code"],
)
HTTP_DURATION = Histogram(
    "obslab_http_request_duration_seconds",
    "HTTP server request duration in seconds.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20),
)
HTTP_IN_PROGRESS = Gauge(
    "obslab_http_requests_in_progress",
    "Current number of in-progress HTTP requests.",
    ["method"],
)
DATABASE_OPERATIONS = Counter(
    "obslab_database_operations_total",
    "Database operations attempted by operation and outcome.",
    ["operation", "outcome"],
)
DATABASE_DURATION = Histogram(
    "obslab_database_operation_duration_seconds",
    "Database operation duration in seconds.",
    ["operation"],
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)
CACHE_OPERATIONS = Counter(
    "obslab_cache_operations_total",
    "Redis cache operations by operation and outcome.",
    ["operation", "outcome"],
)
ORDERS_CREATED = Counter(
    "obslab_orders_created_total",
    "Orders successfully created.",
    ["status"],
)
SIMULATIONS = Counter(
    "obslab_simulations_total",
    "Controlled failure or load simulations invoked.",
    ["kind", "outcome"],
)
ALERT_WEBHOOKS = Counter(
    "obslab_alert_webhooks_total",
    "Alertmanager webhook notifications received by status.",
    ["status"],
)
BUILD_INFO = Info("obslab_build", "Build and runtime metadata for the lab application.")


def initialize_build_info(version: str, environment: str, build_sha: str) -> None:
    BUILD_INFO.info({"version": version, "environment": environment, "build_sha": build_sha})
