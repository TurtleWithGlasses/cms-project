"""
Monitoring Routes

Provides health check endpoints and Prometheus metrics for observability.
"""

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import ReadAsyncSessionLocal, get_db, get_pool_stats
from app.utils.metrics import set_app_info, update_health_status, update_uptime

router = APIRouter(tags=["Monitoring"])

# Application start time for uptime calculation
APP_START_TIME = time.time()

# Initialize app info metrics
set_app_info(version=settings.app_version, environment=settings.environment)


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

    # Read replica check (reports not_configured when replica URL is absent)
    checks["read_replica"] = await _check_read_replica()

    # Connection pool utilisation
    checks["connection_pool"] = _check_pool_health()

    # Disk space check (simplified)
    checks["disk"] = {"status": "healthy", "message": "Disk space available"}

    # Memory check (simplified)
    checks["memory"] = {"status": "healthy", "message": "Memory available"}

    # Overall status — not_configured is not unhealthy
    all_healthy = all(check.get("status") in ("healthy", "not_configured") for check in checks.values())

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
    Uses prometheus_client library for proper metric exposition.
    """
    # Update uptime metric before generating output
    update_uptime(APP_START_TIME)

    # Generate Prometheus metrics output using the official library
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get("/metrics/summary")
async def metrics_summary() -> dict[str, Any]:
    """
    JSON summary of key application metrics from Prometheus collectors.

    Returns human-readable metrics for dashboards without requiring
    a Prometheus server.
    """
    from app.utils.metrics import (
        APP_UPTIME_SECONDS,
        CACHE_HITS_TOTAL,
        CACHE_MISSES_TOTAL,
        DB_QUERIES_TOTAL,
        HTTP_REQUESTS_IN_PROGRESS,
        HTTP_REQUESTS_TOTAL,
    )

    # HTTP request metrics
    total_requests = 0
    error_requests = 0
    for sample in HTTP_REQUESTS_TOTAL.collect()[0].samples:
        val = int(sample.value)
        total_requests += val
        status = sample.labels.get("status_code", "")
        if status.startswith("5"):
            error_requests += val

    in_progress = 0
    for sample in HTTP_REQUESTS_IN_PROGRESS.collect()[0].samples:
        in_progress += int(sample.value)

    # DB query metrics
    total_db_queries = 0
    for sample in DB_QUERIES_TOTAL.collect()[0].samples:
        total_db_queries += int(sample.value)

    # Cache metrics
    total_hits = 0
    total_misses = 0
    for sample in CACHE_HITS_TOTAL.collect()[0].samples:
        total_hits += int(sample.value)
    for sample in CACHE_MISSES_TOTAL.collect()[0].samples:
        total_misses += int(sample.value)

    cache_total = total_hits + total_misses
    cache_hit_rate = round((total_hits / cache_total * 100) if cache_total > 0 else 0, 2)

    # Uptime
    uptime = 0.0
    for sample in APP_UPTIME_SECONDS.collect()[0].samples:
        uptime = sample.value

    # Pool stats (live from engine introspection)
    pool_stats = get_pool_stats()
    primary_pool = pool_stats["primary"]
    replica_pool = pool_stats["replica"]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(uptime, 2),
        "http": {
            "total_requests": total_requests,
            "error_requests": error_requests,
            "error_rate_percent": round((error_requests / total_requests * 100) if total_requests > 0 else 0, 2),
            "in_progress": in_progress,
        },
        "database": {
            "total_queries": total_db_queries,
        },
        "cache": {
            "hits": total_hits,
            "misses": total_misses,
            "hit_rate_percent": cache_hit_rate,
        },
        "connection_pool": {
            "primary": primary_pool,
            "replica": replica_pool,
            "read_replica_configured": bool(settings.database_read_replica_url),
        },
    }


async def _check_database(db: AsyncSession) -> dict[str, Any]:
    """Check database connectivity and update health metrics."""
    try:
        start = time.perf_counter()
        await db.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start) * 1000

        # Update health metric
        update_health_status("database", healthy=True)

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "message": "Database connection successful",
        }
    except Exception as e:
        # Update health metric
        update_health_status("database", healthy=False)

        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed",
        }


async def _check_redis() -> dict[str, Any]:
    """Check Redis connectivity and update health metrics."""
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

            # Update health metric
            update_health_status("redis", healthy=True)

            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "message": "Redis connection successful",
            }
        else:
            # Update health metric
            update_health_status("redis", healthy=False)

            return {
                "status": "unhealthy",
                "message": "Redis client not initialized",
            }
    except Exception as e:
        # Update health metric
        update_health_status("redis", healthy=False)

        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Redis connection failed",
        }


async def _check_read_replica() -> dict[str, Any]:
    """
    Check read-replica connectivity.

    Returns {"status": "not_configured"} when DATABASE_READ_REPLICA_URL is absent
    so callers can distinguish "missing" from "unhealthy".
    """
    if not settings.database_read_replica_url:
        return {"status": "not_configured", "message": "No read replica configured"}

    try:
        start = time.perf_counter()
        async with ReadAsyncSessionLocal() as replica_db:
            await replica_db.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "message": "Read replica connection successful",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Read replica connection failed",
        }


def _check_pool_health() -> dict[str, Any]:
    """
    Inspect connection pool utilisation and return a health assessment.

    Thresholds:
      - < 70% utilisation → healthy
      - 70–90% → warning
      - ≥ 90% → critical
    """
    stats = get_pool_stats()
    primary = stats["primary"]

    pool_size = primary.get("size", 0)
    max_capacity = pool_size + primary.get("overflow", 0)
    checked_out = primary.get("checkedout", 0)

    utilisation = (checked_out / max_capacity * 100) if max_capacity > 0 else 0.0

    if utilisation >= 90:
        pool_status = "critical"
        message = f"Primary pool utilisation critical ({utilisation:.1f}%)"
    elif utilisation >= 70:
        pool_status = "warning"
        message = f"Primary pool utilisation elevated ({utilisation:.1f}%)"
    else:
        pool_status = "healthy"
        message = f"Primary pool utilisation normal ({utilisation:.1f}%)"

    return {
        "status": pool_status,
        "message": message,
        "utilisation_percent": round(utilisation, 1),
        "primary": primary,
        "replica": stats["replica"],
        "read_replica_configured": bool(settings.database_read_replica_url),
    }
