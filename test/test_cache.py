"""
Tests for Cache functionality.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.cache_service import CacheService, LRUCache
from main import app


class TestLRUCache:
    """Tests for in-memory LRU cache."""

    def test_basic_get_set(self):
        """Test basic get and set operations."""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        """Test getting a missing key."""
        cache = LRUCache(max_size=10)

        assert cache.get("missing") is None

    def test_delete(self):
        """Test deleting a key."""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_max_size_eviction(self):
        """Test that LRU eviction works when max size is reached."""
        cache = LRUCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # This should evict key1

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_lru_ordering(self):
        """Test that accessing a key moves it to end."""
        cache = LRUCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it most recently used
        cache.get("key1")

        # Now add key4, which should evict key2 (least recently used)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"  # Still exists
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_clear(self):
        """Test clearing the cache."""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss

        stats = cache.get_stats()

        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestCacheService:
    """Tests for CacheService."""

    def test_service_creation(self):
        """Test creating cache service."""
        service = CacheService()

        assert service._version == "v1"
        assert service._memory is not None

    def test_version_increment(self):
        """Test version increment for cache invalidation."""
        service = CacheService()
        original_version = service._version

        new_version = service.increment_version()

        assert new_version != original_version
        assert new_version.startswith("v")

    def test_get_stats(self):
        """Test getting comprehensive stats."""
        service = CacheService()
        stats = service.get_stats()

        assert "memory_cache" in stats
        assert "service_stats" in stats
        assert "version" in stats
        assert "redis_enabled" in stats


class TestCacheRoutes:
    """Tests for cache management endpoints."""

    @pytest.mark.asyncio
    async def test_get_stats_requires_auth(self):
        """Test that cache stats require authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/cache/stats")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_warm_cache_requires_auth(self):
        """Test that cache warming requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/cache/warm",
                json={"content_limit": 50},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalidate_all_requires_auth(self):
        """Test that invalidating all cache requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/cache/invalidate/all")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_keys_count_requires_auth(self):
        """Test that getting keys count requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/cache/keys/count")

        assert response.status_code == 401
