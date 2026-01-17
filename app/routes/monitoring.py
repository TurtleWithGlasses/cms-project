"""
Monitoring Routes

Provides health check endpoints and Prometheus metrics for observability.
"""

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

router = APIRouter(tags=["Monitoring"])

# Application start time for uptime calculation
APP_START_TIME = time.time()

# Simple in-memory metrics (for demonstration)
# In production, use prometheus_client library
METRICS = {
    "http_requests_total": 0,
    "http_request_duration_seconds": [],
    "db_queries_total": 0,
    "cache_hits_total": 0,
    "cache_misses_total": 0,
}


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    version: str
    uptime_seconds: float


class ReadinessStatus(BaseModel):
    """Readiness check response model."""

    status: str
    timestamp: str
    checks: dict[str, dict[str, Any]]


class DetailedHealth(BaseModel):
    """Detailed health check response model."""

    status: str
    timestamp: str
    version: str
    environment: str
    uptime_seconds: float
    checks: dict[str, dict[str, Any]]


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Liveness probe endpoint.

    Returns basic health status. Used by load balancers and
    orchestrators to determine if the application is alive.

    This endpoint should be fast and not depend on external services.
    """
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.app_version,
        uptime_seconds=round(time.time() - APP_START_TIME, 2),
    )


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_check(db: AsyncSession = Depends(get_db)) -> ReadinessStatus:
    """
    Readiness probe endpoint.

    Checks if the application is ready to handle requests by
    verifying connectivity to required services (database, Redis).

    Used by orchestrators to determine if traffic should be routed
    to this instance.
    """
    checks = {}

    # Check database connectivity
    db_check = await _check_database(db)
    checks["database"] = db_check

    # Check Redis connectivity
    redis_check = await _check_redis()
    checks["redis"] = redis_check

    # Overall status
    all_healthy = all(check.get("status") == "healthy" for check in checks.values())

    return ReadinessStatus(
        status="ready" if all_healthy else "not_ready",
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks,
    )


@router.get("/health/detailed", response_model=DetailedHealth)
async def detailed_health_check(db: AsyncSession = Depends(get_db)) -> DetailedHealth:
    """
    Detailed health check endpoint.

    Provides comprehensive health information including all
    service dependencies and their status.
    """
    checks = {}

    # Database check
    checks["database"] = await _check_database(db)

    # Redis check
    checks["redis"] = await _check_redis()

    # Disk space check (simplified)
    checks["disk"] = {"status": "healthy", "message": "Disk space available"}

    # Memory check (simplified)
    checks["memory"] = {"status": "healthy", "message": "Memory available"}

    # Overall status
    all_healthy = all(check.get("status") == "healthy" for check in checks.values())

    return DetailedHealth(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(time.time() - APP_START_TIME, 2),
        checks=checks,
    )


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    """
    uptime = time.time() - APP_START_TIME

    # Build Prometheus metrics output
    metrics_output = []

    # Application info
    metrics_output.append("# HELP cms_app_info Application information")
    metrics_output.append("# TYPE cms_app_info gauge")
    metrics_output.append(f'cms_app_info{{version="{settings.app_version}",environment="{settings.environment}"}} 1')

    # Uptime
    metrics_output.append("# HELP cms_uptime_seconds Application uptime in seconds")
    metrics_output.append("# TYPE cms_uptime_seconds gauge")
    metrics_output.append(f"cms_uptime_seconds {uptime:.2f}")

    # HTTP requests (would be populated by middleware in production)
    metrics_output.append("# HELP cms_http_requests_total Total HTTP requests")
    metrics_output.append("# TYPE cms_http_requests_total counter")
    metrics_output.append(f"cms_http_requests_total {METRICS['http_requests_total']}")

    # Database queries
    metrics_output.append("# HELP cms_db_queries_total Total database queries")
    metrics_output.append("# TYPE cms_db_queries_total counter")
    metrics_output.append(f"cms_db_queries_total {METRICS['db_queries_total']}")

    # Cache metrics
    metrics_output.append("# HELP cms_cache_hits_total Total cache hits")
    metrics_output.append("# TYPE cms_cache_hits_total counter")
    metrics_output.append(f"cms_cache_hits_total {METRICS['cache_hits_total']}")

    metrics_output.append("# HELP cms_cache_misses_total Total cache misses")
    metrics_output.append("# TYPE cms_cache_misses_total counter")
    metrics_output.append(f"cms_cache_misses_total {METRICS['cache_misses_total']}")

    return Response(
        content="\n".join(metrics_output) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


async def _check_database(db: AsyncSession) -> dict[str, Any]:
    """Check database connectivity."""
    try:
        start = time.perf_counter()
        await db.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "message": "Database connection successful",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed",
        }


async def _check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        from app.utils.session import session_manager

        start = time.perf_counter()

        # Try to connect if not already connected
        if session_manager._redis is None:
            await session_manager.connect()

        # Ping Redis
        if session_manager._redis:
            await session_manager._redis.ping()
            latency_ms = (time.perf_counter() - start) * 1000

            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "message": "Redis connection successful",
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Redis client not initialized",
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Redis connection failed",
        }


def increment_metric(metric_name: str, value: int = 1) -> None:
    """Increment a metric counter."""
    if metric_name in METRICS and isinstance(METRICS[metric_name], int):
        METRICS[metric_name] += value


def record_duration(metric_name: str, duration: float) -> None:
    """Record a duration metric."""
    if metric_name in METRICS and isinstance(METRICS[metric_name], list):
        METRICS[metric_name].append(duration)
        # Keep only last 1000 measurements
        if len(METRICS[metric_name]) > 1000:
            METRICS[metric_name] = METRICS[metric_name][-1000:]
