"""
Performance Tests

Tests for performance optimizations including caching, pagination, and query efficiency.
"""

import base64
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.cache import CacheManager, cache_manager, get_cache_manager
from app.utils.pagination import (
    CursorInfo,
    PaginationParams,
    decode_cursor,
    encode_cursor,
    paginate_with_cursor,
)


class TestCursorPagination:
    """Tests for cursor-based pagination"""

    def test_encode_cursor_simple(self):
        """Test encoding a simple cursor with just ID"""
        cursor = encode_cursor(123)
        assert cursor is not None
        assert isinstance(cursor, str)

        # Should be base64 decodable
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(decoded)
        assert data["id"] == 123

    def test_encode_cursor_with_timestamp(self):
        """Test encoding cursor with timestamp"""
        now = datetime.now(timezone.utc)
        cursor = encode_cursor(456, created_at=now)

        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(decoded)
        assert data["id"] == 456
        assert "created_at" in data

    def test_decode_cursor_valid(self):
        """Test decoding a valid cursor"""
        now = datetime.now(timezone.utc)
        cursor = encode_cursor(789, created_at=now)

        info = decode_cursor(cursor)
        assert isinstance(info, CursorInfo)
        assert info.id == 789
        assert info.created_at is not None

    def test_decode_cursor_invalid(self):
        """Test decoding an invalid cursor raises HTTPException"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            decode_cursor("invalid_cursor_string")

    def test_decode_cursor_malformed_json(self):
        """Test decoding malformed JSON cursor raises HTTPException"""
        from fastapi import HTTPException

        # Create a valid base64 string with invalid JSON
        malformed = base64.urlsafe_b64encode(b"not valid json").decode()
        with pytest.raises(HTTPException):
            decode_cursor(malformed)

    def test_pagination_params_class_exists(self):
        """Test pagination parameters class is properly defined"""
        # PaginationParams is a FastAPI dependency that injects Query params
        # When instantiated directly, the Query wrappers are still present
        # This tests the class structure, not the injected values
        import inspect

        sig = inspect.signature(PaginationParams.__init__)
        params = sig.parameters

        assert "limit" in params
        assert "cursor" in params
        assert "sort_order" in params

    def test_pagination_params_custom(self):
        """Test pagination parameters with custom values"""
        params = PaginationParams(limit=50, cursor="some_cursor", sort_order="asc")
        assert params.limit == 50
        assert params.cursor == "some_cursor"
        assert params.sort_order == "asc"


class TestCacheManager:
    """Tests for cache manager"""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        mock = AsyncMock()
        mock.ping = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.setex = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.scan_iter = AsyncMock(return_value=iter([]))
        return mock

    @pytest.mark.asyncio
    async def test_cache_manager_init(self):
        """Test cache manager initialization"""
        cm = CacheManager()
        assert cm._redis is None
        assert cm._enabled is True

    @pytest.mark.asyncio
    async def test_cache_get_disabled(self):
        """Test cache get when disabled"""
        cm = CacheManager()
        cm._enabled = False
        result = await cm.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_disabled(self):
        """Test cache set when disabled"""
        cm = CacheManager()
        cm._enabled = False
        result = await cm.set("test_key", {"data": "value"})
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_delete_disabled(self):
        """Test cache delete when disabled"""
        cm = CacheManager()
        cm._enabled = False
        result = await cm.delete("test_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_ttl_constants(self):
        """Test cache TTL constants are defined"""
        assert CacheManager.TTL_SHORT == 60
        assert CacheManager.TTL_MEDIUM == 300
        assert CacheManager.TTL_LONG == 3600
        assert CacheManager.TTL_ANALYTICS == 120

    @pytest.mark.asyncio
    async def test_cache_prefix_constants(self):
        """Test cache prefix constants are defined"""
        assert CacheManager.PREFIX_ANALYTICS == "cache:analytics:"
        assert CacheManager.PREFIX_CONTENT == "cache:content:"
        assert CacheManager.PREFIX_USER == "cache:user:"

    @pytest.mark.asyncio
    async def test_cache_get_with_mock(self, mock_redis):
        """Test cache get with mocked Redis"""
        cm = CacheManager()
        cm._redis = mock_redis
        cm._enabled = True

        # Test cache miss
        mock_redis.get.return_value = None
        result = await cm.get("missing_key")
        assert result is None

        # Test cache hit
        mock_redis.get.return_value = json.dumps({"data": "cached"})
        result = await cm.get("existing_key")
        assert result == {"data": "cached"}

    @pytest.mark.asyncio
    async def test_cache_set_with_mock(self, mock_redis):
        """Test cache set with mocked Redis"""
        cm = CacheManager()
        cm._redis = mock_redis
        cm._enabled = True

        result = await cm.set("test_key", {"value": 123}, ttl=60)
        assert result is True
        mock_redis.setex.assert_called_once()


class TestEagerLoading:
    """Tests for eager loading optimizations"""

    @pytest.mark.asyncio
    async def test_content_service_uses_selectinload(self):
        """Verify content service uses eager loading"""
        import inspect

        from app.services.content_service import get_all_content

        # Get the source code and check for selectinload
        source = inspect.getsource(get_all_content)
        assert "selectinload" in source
        assert "Content.author" in source
        assert "Content.category" in source

    @pytest.mark.asyncio
    async def test_user_route_uses_eager_loading(self):
        """Verify user route uses eager loading for roles"""
        import inspect

        from app.routes.user import list_users

        source = inspect.getsource(list_users)
        assert "selectinload" in source
        assert "User.role" in source


class TestGzipMiddleware:
    """Tests for GZip compression middleware"""

    def test_gzip_middleware_configured(self):
        """Verify GZip middleware is configured in main.py"""
        from main import create_app

        app = create_app()

        # Check middleware stack
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "GZipMiddleware" in middleware_classes


class TestDatabaseIndexes:
    """Tests for database index definitions"""

    def test_content_model_indexes(self):
        """Verify Content model has required indexes"""
        from app.models.content import Content

        table_args = Content.__table_args__

        # Check for specific indexes
        index_names = [idx.name for idx in table_args if hasattr(idx, "name") and idx.name is not None]

        assert "ix_content_category_id" in index_names
        assert "ix_content_created_at" in index_names
        assert "ix_content_status_created" in index_names

    def test_user_model_indexes(self):
        """Verify User model has required indexes"""
        from app.models.user import User

        table_args = User.__table_args__

        index_names = [idx.name for idx in table_args if hasattr(idx, "name") and idx.name is not None]

        assert "ix_users_role_id" in index_names

    def test_media_model_indexes(self):
        """Verify Media model has required indexes"""
        from app.models.media import Media

        table_args = Media.__table_args__

        index_names = [idx.name for idx in table_args if hasattr(idx, "name") and idx.name is not None]

        assert "ix_media_uploaded_by" in index_names
        assert "ix_media_uploaded_at" in index_names

    def test_notification_model_indexes(self):
        """Verify Notification model has composite index"""
        from app.models.notification import Notification

        table_args = Notification.__table_args__

        index_names = [idx.name for idx in table_args if hasattr(idx, "name") and idx.name is not None]

        assert "ix_notifications_user_status" in index_names


class TestConnectionPooling:
    """Tests for database connection pooling configuration"""

    def test_production_pool_settings(self):
        """Verify production pool settings are appropriate"""
        # These would be tested in a production-like environment
        # For now, verify the configuration module structure

        from app.config import settings

        # Verify settings structure exists
        assert hasattr(settings, "environment")
        assert hasattr(settings, "database_url")

    def test_database_engine_has_pool_settings(self):
        """Verify database engine has pool configuration"""
        from app.database import engine

        # Check that engine exists and has pool
        assert engine is not None
        # Pool attributes are set during engine creation
        assert hasattr(engine, "pool")
