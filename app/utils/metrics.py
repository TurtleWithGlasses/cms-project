"""
Prometheus Metrics Module

Provides application metrics using the prometheus_client library.
Metrics are exposed at /metrics endpoint for Prometheus scraping.
"""

import time
from collections.abc import Callable
from functools import wraps

from prometheus_client import Counter, Gauge, Histogram, Info
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# =============================================================================
# Application Info
# =============================================================================

APP_INFO = Info("cms_app", "CMS Application information")


def set_app_info(version: str, environment: str) -> None:
    """Set application info labels."""
    APP_INFO.info({"version": version, "environment": environment})


# =============================================================================
# HTTP Request Metrics
# =============================================================================

HTTP_REQUESTS_TOTAL = Counter(
    "cms_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "cms_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "cms_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method"],
)

# =============================================================================
# Database Metrics
# =============================================================================

DB_QUERIES_TOTAL = Counter(
    "cms_db_queries_total",
    "Total database queries executed",
    ["operation"],
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "cms_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

DB_CONNECTIONS_ACTIVE = Gauge(
    "cms_db_connections_active",
    "Number of active database connections",
)

# Connection pool utilisation — updated by pool_monitor background task (every 15 s)
DB_POOL_CHECKED_OUT = Gauge(
    "cms_db_pool_checked_out",
    "Number of DB connections currently checked out from the pool",
    ["engine"],  # "primary" or "replica"
)

DB_POOL_AVAILABLE = Gauge(
    "cms_db_pool_available",
    "Number of DB connections available (checked in) in the pool",
    ["engine"],
)

DB_POOL_OVERFLOW = Gauge(
    "cms_db_pool_overflow",
    "Number of DB connections currently in pool overflow",
    ["engine"],
)

# Redis connectivity — set by CacheManager / RedisSessionManager on connect/disconnect
REDIS_CONNECTED = Gauge(
    "cms_redis_connected",
    "Redis connection status (1 = connected, 0 = disconnected)",
    ["role"],  # "cache" or "session"
)

REDIS_SENTINEL_FAILOVERS = Counter(
    "cms_redis_sentinel_failovers_total",
    "Total Redis Sentinel failover events detected by the application",
)


def update_pool_metrics(engine_label: str, stats: dict) -> None:
    """Push connection-pool stats from get_pool_stats() into Prometheus gauges."""
    checkedout = stats.get("checkedout", 0)
    checkedin = stats.get("checkedin", 0)
    overflow = stats.get("overflow", 0)
    DB_POOL_CHECKED_OUT.labels(engine=engine_label).set(checkedout)
    DB_POOL_AVAILABLE.labels(engine=engine_label).set(checkedin)
    DB_POOL_OVERFLOW.labels(engine=engine_label).set(overflow)


# =============================================================================
# Cache Metrics
# =============================================================================

CACHE_HITS_TOTAL = Counter(
    "cms_cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

CACHE_MISSES_TOTAL = Counter(
    "cms_cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)

CACHE_OPERATIONS_TOTAL = Counter(
    "cms_cache_operations_total",
    "Total cache operations",
    ["operation", "cache_type"],
)

# =============================================================================
# Authentication Metrics
# =============================================================================

AUTH_ATTEMPTS_TOTAL = Counter(
    "cms_auth_attempts_total",
    "Total authentication attempts",
    ["result"],  # success, failure, blocked
)

AUTH_TOKENS_ISSUED_TOTAL = Counter(
    "cms_auth_tokens_issued_total",
    "Total authentication tokens issued",
    ["token_type"],  # access, refresh
)

ACTIVE_SESSIONS = Gauge(
    "cms_active_sessions",
    "Number of active user sessions",
)

# =============================================================================
# Content Metrics
# =============================================================================

CONTENT_OPERATIONS_TOTAL = Counter(
    "cms_content_operations_total",
    "Total content operations",
    ["operation"],  # create, update, delete, publish
)

CONTENT_ITEMS_TOTAL = Gauge(
    "cms_content_items_total",
    "Total content items by status",
    ["status"],  # draft, pending, published
)

# =============================================================================
# Application Health Metrics
# =============================================================================

APP_UPTIME_SECONDS = Gauge(
    "cms_uptime_seconds",
    "Application uptime in seconds",
)

HEALTH_CHECK_STATUS = Gauge(
    "cms_health_check_status",
    "Health check status (1=healthy, 0=unhealthy)",
    ["service"],  # database, redis, disk, memory
)

# =============================================================================
# Prometheus Metrics Middleware
# =============================================================================


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics for Prometheus.

    Tracks:
    - Request count by method, endpoint, and status code
    - Request duration by method and endpoint
    - In-progress requests by method
    """

    # Endpoints to exclude from metrics (to avoid noise)
    EXCLUDED_PATHS = {"/metrics", "/health", "/ready", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip excluded paths
        path = request.url.path
        if path in self.EXCLUDED_PATHS:
            return await call_next(request)

        method = request.method

        # Normalize path for metrics (replace IDs with placeholder)
        endpoint = self._normalize_path(path)

        # Track in-progress requests
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).inc()

        # Time the request
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            # Record duration
            duration = time.perf_counter() - start_time
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)

            # Record request count
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()

            # Decrement in-progress
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()

        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        Normalize URL path for metrics by replacing dynamic segments.

        Examples:
            /api/v1/users/123 -> /api/v1/users/{id}
            /api/v1/content/456/versions/7 -> /api/v1/content/{id}/versions/{id}
        """
        parts = path.split("/")
        normalized = []

        for part in parts:
            if part.isdigit():
                normalized.append("{id}")
            elif part and len(part) == 36 and "-" in part:
                # UUID pattern
                normalized.append("{uuid}")
            else:
                normalized.append(part)

        return "/".join(normalized)


# =============================================================================
# Helper Functions
# =============================================================================


def track_db_query(operation: str = "query"):
    """
    Decorator to track database query metrics.

    Usage:
        @track_db_query("select")
        async def get_user(db, user_id):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time
                DB_QUERIES_TOTAL.labels(operation=operation).inc()
                DB_QUERY_DURATION_SECONDS.labels(operation=operation).observe(duration)

        return wrapper

    return decorator


def record_cache_hit(cache_type: str = "default") -> None:
    """Record a cache hit."""
    CACHE_HITS_TOTAL.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = "default") -> None:
    """Record a cache miss."""
    CACHE_MISSES_TOTAL.labels(cache_type=cache_type).inc()


def record_auth_attempt(result: str) -> None:
    """Record an authentication attempt (success/failure/blocked)."""
    AUTH_ATTEMPTS_TOTAL.labels(result=result).inc()


def record_content_operation(operation: str) -> None:
    """Record a content operation (create/update/delete/publish)."""
    CONTENT_OPERATIONS_TOTAL.labels(operation=operation).inc()


def update_content_counts(draft: int, pending: int, published: int) -> None:
    """Update content item counts by status."""
    CONTENT_ITEMS_TOTAL.labels(status="draft").set(draft)
    CONTENT_ITEMS_TOTAL.labels(status="pending").set(pending)
    CONTENT_ITEMS_TOTAL.labels(status="published").set(published)


def update_health_status(service: str, healthy: bool) -> None:
    """Update health check status for a service."""
    HEALTH_CHECK_STATUS.labels(service=service).set(1 if healthy else 0)


def update_uptime(start_time: float) -> None:
    """Update application uptime."""
    APP_UPTIME_SECONDS.set(time.time() - start_time)
