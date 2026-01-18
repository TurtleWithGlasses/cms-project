"""
Cache Management Routes

API endpoints for cache management and monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.cache_service import CacheService, get_cache_service
from app.utils.cache import CacheManager

router = APIRouter(prefix="/cache", tags=["Cache"])


# ============== Schemas ==============


class CacheStatsResponse(BaseModel):
    """Response for cache statistics."""

    memory_cache: dict
    service_stats: dict
    version: str
    redis_enabled: bool


class RedisInfoResponse(BaseModel):
    """Response for Redis server info."""

    version: str | None
    used_memory: str | None
    connected_clients: int | None
    uptime_days: int | None
    total_commands: int | None
    keyspace_hits: int | None
    keyspace_misses: int | None


class CacheWarmRequest(BaseModel):
    """Request to warm the cache."""

    content_limit: int = Field(50, ge=1, le=500)
    warm_analytics: bool = True


class CacheInvalidateRequest(BaseModel):
    """Request to invalidate cache."""

    pattern: str = Field(..., description="Key pattern to invalidate (e.g., 'content:*')")


class CacheSetRequest(BaseModel):
    """Request to set a cache value."""

    key: str = Field(..., min_length=1, max_length=200)
    value: dict | list | str | int | float | bool
    ttl: int | None = Field(None, ge=1, le=86400)


# ============== Statistics ==============


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> CacheStatsResponse:
    """
    Get cache statistics.

    Returns hit/miss rates, memory usage, and Redis status.
    """
    stats = cache.get_stats()
    return CacheStatsResponse(**stats)


@router.get("/redis-info")
async def get_redis_info(
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get Redis server information.

    Returns version, memory usage, and command statistics.
    """
    info = await cache.get_redis_info()
    if not info:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is not available",
        )
    return info


@router.get("/keys/count")
async def get_keys_count(
    pattern: str = "*",
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Count cached keys matching a pattern.
    """
    count = await cache.get_cached_keys_count(pattern)
    return {"pattern": pattern, "count": count}


# ============== Cache Warming ==============


@router.post("/warm")
async def warm_cache(
    data: CacheWarmRequest,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Warm the cache with popular content.

    Pre-populates cache to improve response times.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    content_count = await cache.warm_popular_content(db, limit=data.content_limit)
    analytics_success = False

    if data.warm_analytics:
        analytics_success = await cache.warm_analytics(db)

    return {
        "content_cached": content_count,
        "analytics_warmed": analytics_success,
        "message": f"Cache warming complete: {content_count} content items cached",
    }


# ============== Cache Invalidation ==============


@router.post("/invalidate")
async def invalidate_cache(
    data: CacheInvalidateRequest,
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Invalidate cache entries matching a pattern.

    Patterns:
    - 'content:*' - All content cache
    - 'analytics:*' - All analytics cache
    - 'user:*' - All user cache
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    deleted = await cache.invalidate_by_pattern(data.pattern)
    return {
        "pattern": data.pattern,
        "deleted": deleted,
        "message": f"Invalidated {deleted} cache entries",
    }


@router.post("/invalidate/content/{content_id}")
async def invalidate_content_cache(
    content_id: int,
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Invalidate cache for a specific content item.
    """
    key = f"{CacheManager.PREFIX_CONTENT}{content_id}"
    deleted = await cache.delete(key)
    return {
        "content_id": content_id,
        "deleted": deleted,
        "message": f"Content cache {'invalidated' if deleted else 'not found'}",
    }


@router.post("/invalidate/all")
async def invalidate_all_cache(
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Invalidate all cache by incrementing version.

    This is a lightweight operation that makes all existing
    cache entries obsolete without actually deleting them.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    new_version = cache.increment_version()
    return {
        "new_version": new_version,
        "message": "All cache invalidated via version increment",
    }


# ============== Manual Cache Operations ==============


@router.get("/get/{key}")
async def get_cache_value(
    key: str,
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get a cached value by key.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    value = await cache.get(key)
    return {
        "key": key,
        "value": value,
        "found": value is not None,
    }


@router.post("/set")
async def set_cache_value(
    data: CacheSetRequest,
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Set a cache value.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    success = await cache.set(data.key, data.value, data.ttl)
    return {
        "key": data.key,
        "success": success,
        "ttl": data.ttl or CacheManager.TTL_MEDIUM,
    }


@router.delete("/delete/{key}")
async def delete_cache_value(
    key: str,
    cache: CacheService = Depends(get_cache_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete a cached value.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    deleted = await cache.delete(key)
    return {
        "key": key,
        "deleted": deleted,
    }
