import logging
import time
import uuid

from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.logging_config import request_id_context
from app.metrics import HTTP_DURATION, HTTP_IN_PROGRESS, HTTP_REQUESTS
from app.telemetry import current_trace_exemplar

logger = logging.getLogger("app.http")


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_request_id = request.headers.get("x-request-id", "")
        request_id = (
            incoming_request_id
            if incoming_request_id and len(incoming_request_id) <= 128
            else str(uuid.uuid4())
        )
        token = request_id_context.set(request_id)
        started_at = time.perf_counter()
        method = request.method
        status_code = 500
        response = None
        HTTP_IN_PROGRESS.labels(method).inc()

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("request.id", request_id)

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        except Exception:
            logger.exception(
                "http.request_unhandled_exception",
                extra={"method": method, "path": request.url.path},
            )
            raise
        finally:
            duration = time.perf_counter() - started_at
            route_object = request.scope.get("route")
            route = getattr(route_object, "path", "unmatched")
            if route != "/metrics":
                HTTP_REQUESTS.labels(method, route, str(status_code)).inc()
                HTTP_DURATION.labels(method, route).observe(
                    duration, exemplar=current_trace_exemplar()
                )
                logger.info(
                    "http.request_completed",
                    extra={
                        "http_method": method,
                        "http_route": route,
                        "http_status_code": status_code,
                        "duration_ms": round(duration * 1_000, 3),
                        "client_ip": request.client.host if request.client else "unknown",
                    },
                )
            HTTP_IN_PROGRESS.labels(method).dec()
            request_id_context.reset(token)
