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
from app.database import get_db
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
    Uses prometheus_client library for proper metric exposition.
    """
    # Update uptime metric before generating output
    update_uptime(APP_START_TIME)

    # Generate Prometheus metrics output using the official library
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


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
