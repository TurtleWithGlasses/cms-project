"""
Tests for Core Components - API Versioning, Config, and Pagination.

These tests cover critical infrastructure components that ensure
proper API versioning, configuration management, and pagination.
"""

import base64
import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api import API_V1_PREFIX, api_v1_router, create_api_router
from app.config import Settings
from app.utils.pagination import (
    CursorInfo,
    PaginatedResponse,
    PaginationParams,
    decode_cursor,
    encode_cursor,
)


class TestAPIVersioning:
    """Tests for API versioning module."""

    def test_api_v1_prefix_value(self):
        """Test that API v1 prefix is correctly defined."""
        assert API_V1_PREFIX == "/api/v1"

    def test_api_v1_router_exists(self):
        """Test that pre-configured v1 router exists."""
        assert api_v1_router is not None
        assert api_v1_router.prefix == API_V1_PREFIX

    def test_create_api_router_default(self):
        """Test creating router with default parameters."""
        router = create_api_router()
        assert router.prefix == "/api/v1"
        assert router.include_in_schema is True

    def test_create_api_router_with_prefix(self):
        """Test creating router with custom prefix."""
        router = create_api_router(prefix="/users")
        assert router.prefix == "/api/v1/users"

    def test_create_api_router_with_tags(self):
        """Test creating router with tags."""
        router = create_api_router(prefix="/content", tags=["Content"])
        assert router.prefix == "/api/v1/content"
        assert router.tags == ["Content"]

    def test_create_api_router_v2(self):
        """Test creating router for v2 API."""
        router = create_api_router(prefix="/items", version="v2")
        assert router.prefix == "/api/v2/items"

    def test_create_api_router_exclude_from_schema(self):
        """Test creating router excluded from schema."""
        router = create_api_router(include_in_schema=False)
        assert router.include_in_schema is False

    def test_create_api_router_empty_prefix(self):
        """Test creating router with empty prefix."""
        router = create_api_router(prefix="")
        assert router.prefix == "/api/v1"


class TestConfigSettings:
    """Tests for configuration settings."""

    def test_settings_has_required_fields(self):
        """Test that settings has all required fields."""
        # Create settings with minimum required fields
        settings = Settings(
            database_url="postgresql://localhost/test",
            secret_key="test-secret-key",
        )

        assert settings.database_url == "postgresql://localhost/test"
        assert settings.secret_key == "test-secret-key"

    def test_settings_default_values(self):
        """Test settings default values."""
        settings = Settings(
            database_url="postgresql://localhost/test",
            secret_key="test-secret-key",
        )

        # Verify core settings fields exist and have reasonable values
        assert settings.app_name is not None
        assert settings.app_version is not None
        assert isinstance(settings.debug, bool)
        assert settings.environment in ["development", "production", "testing"]
        assert settings.access_token_expire_minutes > 0

    def test_settings_redis_defaults(self):
        """Test Redis-related default settings."""
        settings = Settings(
            database_url="postgresql://localhost/test",
            secret_key="test-secret-key",
        )

        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.redis_db == 0
        assert settings.redis_password is None
        assert settings.session_expire_seconds == 3600

    def test_settings_cors_defaults(self):
        """Test CORS default settings."""
        settings = Settings(
            database_url="postgresql://localhost/test",
            secret_key="test-secret-key",
        )

        assert "http://localhost:3000" in settings.allowed_origins
        assert "http://localhost:8000" in settings.allowed_origins

    def test_settings_smtp_defaults(self):
        """Test SMTP default settings."""
        settings = Settings(
            database_url="postgresql://localhost/test",
            secret_key="test-secret-key",
        )

        assert settings.smtp_host == "smtp.gmail.com"
        assert settings.smtp_port == 587
        assert settings.smtp_from == "noreply@cms-project.com"


class TestCursorEncoding:
    """Tests for cursor-based pagination encoding/decoding."""

    def test_encode_cursor_basic(self):
        """Test basic cursor encoding."""
        cursor = encode_cursor(item_id=123)
        assert cursor is not None
        assert isinstance(cursor, str)

        # Verify it's valid base64
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(decoded)
        assert data["id"] == 123

    def test_encode_cursor_with_created_at(self):
        """Test cursor encoding with created_at timestamp."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0)
        cursor = encode_cursor(item_id=456, created_at=timestamp)

        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(decoded)
        assert data["id"] == 456
        assert "created_at" in data

    def test_encode_cursor_with_sort_value(self):
        """Test cursor encoding with sort value."""
        cursor = encode_cursor(item_id=789, sort_value="title_a")

        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(decoded)
        assert data["id"] == 789
        assert data["sort_value"] == "title_a"

    def test_decode_cursor_basic(self):
        """Test basic cursor decoding."""
        cursor = encode_cursor(item_id=100)
        info = decode_cursor(cursor)

        assert isinstance(info, CursorInfo)
        assert info.id == 100
        assert info.created_at is None
        assert info.sort_value is None

    def test_decode_cursor_with_created_at(self):
        """Test cursor decoding with created_at."""
        timestamp = datetime(2025, 6, 20, 15, 45, 30)
        cursor = encode_cursor(item_id=200, created_at=timestamp)
        info = decode_cursor(cursor)

        assert info.id == 200
        assert info.created_at == timestamp

    def test_decode_cursor_with_sort_value(self):
        """Test cursor decoding with sort value."""
        cursor = encode_cursor(item_id=300, sort_value="custom_sort")
        info = decode_cursor(cursor)

        assert info.id == 300
        assert info.sort_value == "custom_sort"

    def test_decode_cursor_invalid_base64(self):
        """Test that invalid base64 raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            decode_cursor("not-valid-base64!!!")

        assert exc_info.value.status_code == 400
        assert "Invalid pagination cursor" in exc_info.value.detail

    def test_decode_cursor_invalid_json(self):
        """Test that invalid JSON raises HTTPException."""
        # Valid base64 but not valid JSON
        invalid_cursor = base64.urlsafe_b64encode(b"not json").decode()

        with pytest.raises(HTTPException) as exc_info:
            decode_cursor(invalid_cursor)

        assert exc_info.value.status_code == 400

    def test_decode_cursor_missing_id(self):
        """Test that cursor without id raises HTTPException."""
        cursor_data = json.dumps({"created_at": "2025-01-01T00:00:00"})
        invalid_cursor = base64.urlsafe_b64encode(cursor_data.encode()).decode()

        with pytest.raises(HTTPException) as exc_info:
            decode_cursor(invalid_cursor)

        assert exc_info.value.status_code == 400

    def test_encode_decode_roundtrip(self):
        """Test complete encode/decode roundtrip."""
        original_id = 999
        original_time = datetime(2025, 12, 31, 23, 59, 59)
        original_sort = "z_sort_value"

        cursor = encode_cursor(item_id=original_id, created_at=original_time, sort_value=original_sort)

        info = decode_cursor(cursor)

        assert info.id == original_id
        assert info.created_at == original_time
        assert info.sort_value == original_sort


class TestCursorInfo:
    """Tests for CursorInfo dataclass."""

    def test_cursor_info_defaults(self):
        """Test CursorInfo with only required fields."""
        info = CursorInfo(id=1)
        assert info.id == 1
        assert info.created_at is None
        assert info.sort_value is None

    def test_cursor_info_full(self):
        """Test CursorInfo with all fields."""
        timestamp = datetime(2025, 5, 10)
        info = CursorInfo(id=42, created_at=timestamp, sort_value="test")

        assert info.id == 42
        assert info.created_at == timestamp
        assert info.sort_value == "test"


class TestPaginatedResponse:
    """Tests for PaginatedResponse model."""

    def test_paginated_response_basic(self):
        """Test basic PaginatedResponse creation."""
        response = PaginatedResponse(
            items=[{"id": 1}, {"id": 2}],
            total=100,
            has_next=True,
            has_previous=False,
        )

        assert len(response.items) == 2
        assert response.total == 100
        assert response.has_next is True
        assert response.has_previous is False
        assert response.next_cursor is None
        assert response.prev_cursor is None

    def test_paginated_response_with_cursors(self):
        """Test PaginatedResponse with cursors."""
        response = PaginatedResponse(
            items=[{"id": 3}],
            total=50,
            has_next=True,
            has_previous=True,
            next_cursor="abc123",
            prev_cursor="xyz789",
        )

        assert response.next_cursor == "abc123"
        assert response.prev_cursor == "xyz789"

    def test_paginated_response_empty(self):
        """Test PaginatedResponse with no items."""
        response = PaginatedResponse(
            items=[],
            total=0,
            has_next=False,
            has_previous=False,
        )

        assert len(response.items) == 0
        assert response.total == 0
        assert response.has_next is False
        assert response.has_previous is False


class TestPaginationParams:
    """Tests for PaginationParams dependency."""

    def test_pagination_params_class_exists(self):
        """Test PaginationParams class can be imported and instantiated."""
        # PaginationParams uses FastAPI Query() for defaults,
        # so we test with explicit values (as FastAPI would provide)
        params = PaginationParams(limit=20, cursor=None, sort_order="desc")

        assert params.limit == 20
        assert params.cursor is None
        assert params.sort_order == "desc"

    def test_pagination_params_custom(self):
        """Test PaginationParams with custom values."""
        params = PaginationParams(limit=50, cursor="test_cursor", sort_order="asc")

        assert params.limit == 50
        assert params.cursor == "test_cursor"
        assert params.sort_order == "asc"

    def test_pagination_params_has_attributes(self):
        """Test PaginationParams has required attributes."""
        params = PaginationParams(limit=10, cursor="abc", sort_order="asc")

        assert hasattr(params, "limit")
        assert hasattr(params, "cursor")
        assert hasattr(params, "sort_order")


class TestNotificationModelDefaults:
    """Additional tests for notification model defaults."""

    def test_notification_preference_partial_override(self):
        """Test that partial overrides work correctly."""
        from app.models.notification_preference import (
            DigestFrequency,
            NotificationCategory,
            NotificationPreference,
        )

        # Override only some values
        pref = NotificationPreference(
            user_id=1,
            category=NotificationCategory.SECURITY,
            email_enabled=False,
            push_enabled=True,
        )

        # Overridden values
        assert pref.email_enabled is False
        assert pref.push_enabled is True

        # Default values preserved
        assert pref.in_app_enabled is True
        assert pref.sms_enabled is False
        assert pref.digest_frequency == DigestFrequency.IMMEDIATE

    def test_notification_template_default_active(self):
        """Test NotificationTemplate is active by default."""
        from app.models.notification_preference import (
            NotificationCategory,
            NotificationTemplate,
        )

        template = NotificationTemplate(
            name="test_template",
            category=NotificationCategory.SYSTEM,
            subject="Test Subject",
            body_text="Test body",
        )

        assert template.is_active is True

    def test_notification_template_override_active(self):
        """Test NotificationTemplate active can be overridden."""
        from app.models.notification_preference import (
            NotificationCategory,
            NotificationTemplate,
        )

        template = NotificationTemplate(
            name="inactive_template",
            category=NotificationCategory.SYSTEM,
            subject="Test Subject",
            body_text="Test body",
            is_active=False,
        )

        assert template.is_active is False

    def test_notification_preference_repr(self):
        """Test NotificationPreference string representation."""
        from app.models.notification_preference import (
            NotificationCategory,
            NotificationPreference,
        )

        pref = NotificationPreference(
            user_id=42,
            category=NotificationCategory.CONTENT,
        )
        pref.id = 1

        repr_str = repr(pref)
        assert "NotificationPreference" in repr_str
        assert "42" in repr_str

    def test_notification_template_repr(self):
        """Test NotificationTemplate string representation."""
        from app.models.notification_preference import (
            NotificationCategory,
            NotificationTemplate,
        )

        template = NotificationTemplate(
            name="test_repr",
            category=NotificationCategory.WORKFLOW,
            subject="Subject",
            body_text="Body",
        )
        template.id = 5

        repr_str = repr(template)
        assert "NotificationTemplate" in repr_str
        assert "test_repr" in repr_str
