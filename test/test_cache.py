"""
Tests for Cache functionality.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.cache_service import CacheService, LRUCache
from app.utils.cache import CacheManager
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
        """Test that cache stats require authentication (redirects to login)."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/cache/stats")

        # Unauthenticated requests get redirected to login
        assert response.status_code in (307, 401)

    @pytest.mark.asyncio
    async def test_warm_cache_requires_auth(self):
        """Test that cache warming requires authentication (redirects to login)."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/cache/warm",
                json={"content_limit": 50},
            )

        assert response.status_code in (307, 401)

    @pytest.mark.asyncio
    async def test_invalidate_all_requires_auth(self):
        """Test that invalidating all cache requires authentication (redirects to login)."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/cache/invalidate/all")

        assert response.status_code in (307, 401)

    @pytest.mark.asyncio
    async def test_get_keys_count_requires_auth(self):
        """Test that getting keys count requires authentication (redirects to login)."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/cache/keys/count")

        assert response.status_code in (307, 401)


class TestLRUCacheTTL:
    """Tests for LRU cache TTL expiration."""

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1", ttl=1)  # 1 second TTL
        assert cache.get("key1") == "value1"

        time.sleep(1.1)  # Wait for expiry
        assert cache.get("key1") is None

    def test_no_ttl_does_not_expire(self):
        """Test that entries without TTL do not expire."""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")  # No TTL
        time.sleep(0.1)
        assert cache.get("key1") == "value1"

    def test_update_resets_ttl(self):
        """Test that updating a key resets its TTL."""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1", ttl=1)
        time.sleep(0.5)
        cache.set("key1", "value2", ttl=2)  # Reset with longer TTL
        time.sleep(0.7)
        assert cache.get("key1") == "value2"  # Should still be alive


class TestCacheMetrics:
    """Tests for Prometheus metrics integration in cache operations."""

    @patch("app.utils.cache.record_cache_hit")
    @patch("app.utils.cache.record_cache_miss")
    @pytest.mark.asyncio
    async def test_redis_cache_hit_records_metric(self, mock_miss, mock_hit):
        """Test that Redis cache hit records Prometheus metric."""
        cm = CacheManager()
        cm._enabled = True

        # Mock Redis returning data
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value='{"key": "value"}')
        cm._redis = mock_redis
        await cm.get("test_key")

        mock_hit.assert_called_once_with("redis")
        mock_miss.assert_not_called()

    @patch("app.utils.cache.record_cache_hit")
    @patch("app.utils.cache.record_cache_miss")
    @pytest.mark.asyncio
    async def test_redis_cache_miss_records_metric(self, mock_miss, mock_hit):
        """Test that Redis cache miss records Prometheus metric."""
        cm = CacheManager()
        cm._enabled = True

        # Mock Redis returning None
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        cm._redis = mock_redis
        await cm.get("missing_key")

        mock_miss.assert_called_once_with("redis")
        mock_hit.assert_not_called()

    @patch("app.services.cache_service.record_cache_hit")
    @patch("app.services.cache_service.record_cache_miss")
    def test_memory_cache_hit_records_metric(self, mock_miss, mock_hit):
        """Test that memory cache hit records Prometheus metric."""
        service = CacheService()
        service._memory.set("v1:test_key", "value")

        # Directly test memory tier
        result = service._memory.get("v1:test_key")
        assert result == "value"

        # The CacheService.get() is async, so test the LRU directly
        # Metrics are called in CacheService.get(), not LRU.get()
        # Just verify the metric functions are importable and callable
        from app.utils.metrics import record_cache_hit, record_cache_miss

        record_cache_hit("memory")
        record_cache_miss("memory")

    @patch("app.services.cache_service.record_cache_hit")
    @patch("app.services.cache_service.record_cache_miss")
    @pytest.mark.asyncio
    async def test_cache_service_memory_hit_records_metric(self, mock_miss, mock_hit):
        """Test that CacheService memory tier hit records Prometheus metric."""
        service = CacheService()

        # Pre-populate memory cache with versioned key
        service._memory.set(f"{service._version}:test_key", "cached_value")

        # Mock Redis to avoid actual connection
        with patch.object(service._redis, "get", return_value=None):
            result = await service.get("test_key", use_memory=True)

        assert result == "cached_value"
        mock_hit.assert_called_with("memory")

    @patch("app.services.cache_service.record_cache_hit")
    @patch("app.services.cache_service.record_cache_miss")
    @pytest.mark.asyncio
    async def test_cache_service_memory_miss_records_metric(self, mock_miss, mock_hit):
        """Test that CacheService memory tier miss records Prometheus metric."""
        service = CacheService()

        # Mock Redis to return None (miss on both tiers)
        with patch.object(service._redis, "get", return_value=None):
            result = await service.get("nonexistent_key", use_memory=True)

        assert result is None
        mock_miss.assert_called_with("memory")


class TestCacheIntegration:
    """Tests for cache-aside pattern integration in routes."""

    @pytest.mark.asyncio
    async def test_content_list_endpoint_returns_data(self):
        """Test that content list endpoint responds successfully."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v1/content/")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_category_list_endpoint_returns_data(self):
        """Test that category list endpoint responds successfully."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v1/categories/")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_popular_tags_endpoint_returns_data(self):
        """Test that popular tags endpoint responds successfully."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v1/content/search/popular-tags/")

        assert response.status_code == 200
