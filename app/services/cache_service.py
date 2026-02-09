"""
Advanced Cache Service

Provides advanced caching features including:
- Cache warming for popular content
- Cache statistics and monitoring
- Multi-tier caching (memory + Redis)
- Cache versioning
- Event-based invalidation
"""

import asyncio
import logging
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content
from app.utils.cache import CacheManager, cache_manager
from app.utils.metrics import record_cache_hit, record_cache_miss

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total * 100


class LRUCache:
    """
    Simple in-memory LRU cache for frequently accessed data.

    First tier of multi-tier caching (before Redis).
    """

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._stats = CacheStats()

    def get(self, key: str) -> Any | None:
        """Get value and move to end (most recently used)."""
        if key in self._cache:
            self._cache.move_to_end(key)
            value, expiry = self._cache[key]
            if expiry and datetime.now(timezone.utc) > expiry:
                del self._cache[key]
                self._stats.misses += 1
                return None
            self._stats.hits += 1
            return value
        self._stats.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value with optional TTL."""
        expiry = None
        if ttl:
            from datetime import timedelta

            expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (value, expiry)

        # Evict oldest if over capacity
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

        self._stats.sets += 1

    def delete(self, key: str) -> bool:
        """Delete a key."""
        if key in self._cache:
            del self._cache[key]
            self._stats.deletes += 1
            return True
        return False

    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "hit_rate": f"{self._stats.hit_rate:.2f}%",
        }


class CacheService:
    """
    Advanced cache service with multi-tier caching.

    Tier 1: In-memory LRU cache (fastest, limited size)
    Tier 2: Redis (distributed, persistent)
    """

    # Cache key prefixes
    PREFIX_POPULAR = "cache:popular:"
    PREFIX_WARMED = "cache:warmed:"
    PREFIX_VERSION = "cache:version:"

    def __init__(self, redis_cache: CacheManager | None = None):
        self._redis = redis_cache or cache_manager
        self._memory = LRUCache(max_size=500)
        self._stats = CacheStats()
        self._version = "v1"

    async def get(self, key: str, use_memory: bool = True) -> Any | None:
        """
        Get value from multi-tier cache.

        Checks memory first, then Redis.
        """
        versioned_key = self._versioned_key(key)

        # Tier 1: Memory cache
        if use_memory:
            value = self._memory.get(versioned_key)
            if value is not None:
                self._stats.hits += 1
                record_cache_hit("memory")
                return value
            record_cache_miss("memory")

        # Tier 2: Redis cache (metrics recorded by CacheManager.get)
        value = await self._redis.get(versioned_key)
        if value is not None:
            # Promote to memory cache
            if use_memory:
                self._memory.set(versioned_key, value, ttl=60)
            self._stats.hits += 1
            return value

        self._stats.misses += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        use_memory: bool = True,
    ) -> bool:
        """
        Set value in multi-tier cache.

        Writes to both memory and Redis.
        """
        versioned_key = self._versioned_key(key)
        ttl = ttl or CacheManager.TTL_MEDIUM

        # Tier 1: Memory cache
        if use_memory:
            self._memory.set(versioned_key, value, min(ttl, 60))

        # Tier 2: Redis cache
        result = await self._redis.set(versioned_key, value, ttl)
        if result:
            self._stats.sets += 1
        else:
            self._stats.errors += 1

        return result

    async def delete(self, key: str) -> bool:
        """Delete from all cache tiers."""
        versioned_key = self._versioned_key(key)

        # Delete from memory
        self._memory.delete(versioned_key)

        # Delete from Redis
        result = await self._redis.delete(versioned_key)
        if result:
            self._stats.deletes += 1

        return result

    async def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        versioned_pattern = self._versioned_key(pattern)

        # Clear memory cache (can't pattern match, so clear all)
        self._memory.clear()

        # Clear Redis by pattern
        return await self._redis.delete_pattern(versioned_pattern)

    def _versioned_key(self, key: str) -> str:
        """Add version prefix to key for cache versioning."""
        return f"{self._version}:{key}"

    def increment_version(self) -> str:
        """
        Increment cache version to invalidate all entries.

        This is a lightweight way to invalidate the entire cache
        without actually deleting keys.
        """
        import time

        self._version = f"v{int(time.time())}"
        self._memory.clear()
        logger.info(f"Cache version incremented to {self._version}")
        return self._version

    # ============== Cache Warming ==============

    async def warm_popular_content(self, db: AsyncSession, limit: int = 50) -> int:
        """
        Pre-populate cache with popular content.

        Fetches most viewed/recent content and caches it.
        """
        try:
            # Get most recent published content
            result = await db.execute(
                select(Content).where(Content.status == "published").order_by(Content.published_at.desc()).limit(limit)
            )
            contents = result.scalars().all()

            warmed_count = 0
            for content in contents:
                cache_key = f"{CacheManager.PREFIX_CONTENT}{content.id}"
                cache_value = {
                    "id": content.id,
                    "title": content.title,
                    "slug": content.slug,
                    "excerpt": content.excerpt,
                    "status": content.status,
                    "published_at": content.published_at.isoformat() if content.published_at else None,
                }

                await self.set(cache_key, cache_value, ttl=CacheManager.TTL_LONG)
                warmed_count += 1

            logger.info(f"Cache warming complete: {warmed_count} content items cached")
            return warmed_count

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return 0

    async def warm_analytics(self, db: AsyncSession) -> bool:
        """Pre-calculate and cache common analytics."""
        try:
            # Get content counts by status
            result = await db.execute(select(Content.status, func.count(Content.id)).group_by(Content.status))
            status_counts = {row[0]: row[1] for row in result}

            # Cache the result
            await self.set(
                f"{CacheManager.PREFIX_ANALYTICS}status_counts",
                status_counts,
                ttl=CacheManager.TTL_ANALYTICS,
            )

            logger.info("Analytics cache warmed")
            return True

        except Exception as e:
            logger.error(f"Analytics cache warming failed: {e}")
            return False

    # ============== Statistics ==============

    def get_stats(self) -> dict:
        """Get comprehensive cache statistics."""
        return {
            "memory_cache": self._memory.get_stats(),
            "service_stats": {
                "hits": self._stats.hits,
                "misses": self._stats.misses,
                "sets": self._stats.sets,
                "deletes": self._stats.deletes,
                "errors": self._stats.errors,
                "hit_rate": f"{self._stats.hit_rate:.2f}%",
            },
            "version": self._version,
            "redis_enabled": self._redis._enabled,
        }

    async def get_redis_info(self) -> dict | None:
        """Get Redis server info."""
        try:
            if not self._redis._redis:
                await self._redis.connect()
            if not self._redis._redis:
                return None

            info = await self._redis._redis.info()
            return {
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "uptime_days": info.get("uptime_in_days"),
                "total_commands": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return None

    async def get_cached_keys_count(self, pattern: str = "*") -> int:
        """Count cached keys matching pattern."""
        try:
            if not self._redis._redis:
                await self._redis.connect()
            if not self._redis._redis:
                return 0

            count = 0
            async for _ in self._redis._redis.scan_iter(match=pattern):
                count += 1
            return count
        except Exception as e:
            logger.error(f"Failed to count keys: {e}")
            return 0


# Global cache service instance
cache_service = CacheService()


async def get_cache_service() -> CacheService:
    """FastAPI dependency for CacheService."""
    return cache_service


# ============== Cache Warming Scheduler ==============


async def schedule_cache_warming(db: AsyncSession, interval_minutes: int = 30) -> None:
    """
    Background task to periodically warm the cache.

    Should be started on application startup.
    """
    while True:
        try:
            await cache_service.warm_popular_content(db)
            await cache_service.warm_analytics(db)
        except Exception as e:
            logger.error(f"Scheduled cache warming failed: {e}")

        await asyncio.sleep(interval_minutes * 60)
