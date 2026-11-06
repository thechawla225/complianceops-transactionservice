"""Prometheus metrics (Phase 08.1): RED metrics for every route, plus screening and alerting counters.

Same RED module as the gateway service, so dashboards and SLO queries work the same across services.

GET /metrics serves them in the Prometheus text format. Kubernetes probes (/healthz) and the scrape itself
(/metrics) are not counted, so probe traffic can't make availability look better than it is.
"""
import time

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# Same buckets as the gateway: 0.3 s is a boundary because the end-to-end SLO is "95% of requests faster than 300 ms",
# and a histogram can only answer "how many were faster than X" when X is one of its bucket boundaries.
LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0)
EXCLUDED_PATHS = {"/healthz", "/metrics"}

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled, by route template and status code.",
    ["method", "route", "status"],
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds, by route template.",
    ["method", "route"],
    buckets=LATENCY_BUCKETS,
)
TRANSACTIONS_SCREENED = Counter(
    "transactions_screened_total",
    "Transactions screened against the watchlist, by verdict (clear or flagged).",
    ["verdict"],
)
# A flagged payment whose alert never reaches the queue is the worst silent failure in this system: alert on any increase.
SQS_PUBLISH_FAILURES = Counter(
    "sqs_publish_failures_total",
    "Flagged transactions that could not be published to the alert queue (SQS).",
)

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def record_request(request: Request, call_next):
    """HTTP middleware: count and time every request except probes and scrapes."""
    if request.url.path in EXCLUDED_PATHS:
        return await call_next(request)
    start = time.perf_counter()
    status = 500  # an exception that escapes every handler is served as a 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # The route template ("/transactions/{transaction_id}"), never the raw path: raw paths would create one
        # time series per transaction ID and eventually overload Prometheus (unbounded label cardinality).
        route = request.scope.get("route")
        template = getattr(route, "path", None) or "unmatched"
        HTTP_REQUESTS.labels(request.method, template, str(status)).inc()
        HTTP_DURATION.labels(request.method, template).observe(time.perf_counter() - start)
