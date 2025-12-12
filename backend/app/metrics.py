from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "http_requests",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)
SOFT_LAUNCH_REQUESTS = Counter(
    "soft_launch_tenant_requests_total",
    "Requests served for soft-launch tenants",
    ["path"],
)
FEEDBACK_SUBMISSIONS = Counter(
    "feedback_submissions_total",
    "Feedback submissions",
    ["tenant_slug"],
)
ADMIN_ACTIONS = Counter(
    "admin_actions_total",
    "Admin actions performed",
    ["action"],
)
AI_USAGE = Counter(
    "ai_usage_total",
    "AI calls by tenant",
    ["tenant_id", "action"],
)
INVOICES_CREATED = Counter(
    "invoices_created_total",
    "Invoices created per tenant",
    ["tenant_id"],
)
PAYMENTS_CREATED = Counter(
    "payments_created_total",
    "Payments created per tenant",
    ["tenant_id"],
)
EXPENSES_CREATED = Counter(
    "expenses_created_total",
    "Expenses created per tenant",
    ["tenant_id"],
)
AI_FORECASTS_CALLED = Counter(
    "ai_forecasts_called_total",
    "Forecast requests submitted to AI",
    ["tenant_id"],
)
ANOMALIES_DETECTED = Counter(
    "anomalies_detected_total",
    "Anomaly detection runs",
    ["tenant_id"],
)


async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        REQUEST_COUNT.labels(method=request.method, path=path, status=str(status_code)).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration)


def setup_metrics(app: FastAPI) -> None:
    """Register metrics middleware and endpoint once."""
    if getattr(app.state, "metrics_enabled", False):
        return
    app.middleware("http")(metrics_middleware)
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False, tags=["internal"])
    app.state.metrics_enabled = True


__all__ = [
    "setup_metrics",
    "metrics_endpoint",
    "metrics_middleware",
    "SOFT_LAUNCH_REQUESTS",
    "FEEDBACK_SUBMISSIONS",
    "ADMIN_ACTIONS",
    "AI_USAGE",
    "INVOICES_CREATED",
    "PAYMENTS_CREATED",
    "EXPENSES_CREATED",
    "AI_FORECASTS_CALLED",
    "ANOMALIES_DETECTED",
]
