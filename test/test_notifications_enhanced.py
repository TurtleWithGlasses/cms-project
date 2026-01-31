"""
Tests for enhanced Notification functionality.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.models.notification_preference import (
    DigestFrequency,
    NotificationCategory,
    NotificationChannel,
    NotificationPreference,
    NotificationTemplate,
)
from main import app


class TestNotificationEnums:
    """Tests for notification enum types."""

    def test_notification_categories(self):
        """Test notification category values."""
        assert NotificationCategory.CONTENT.value == "content"
        assert NotificationCategory.COMMENTS.value == "comments"
        assert NotificationCategory.WORKFLOW.value == "workflow"
        assert NotificationCategory.SECURITY.value == "security"
        assert NotificationCategory.SYSTEM.value == "system"

    def test_notification_channels(self):
        """Test notification channel values."""
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.IN_APP.value == "in_app"
        assert NotificationChannel.PUSH.value == "push"
        assert NotificationChannel.SMS.value == "sms"

    def test_digest_frequencies(self):
        """Test digest frequency values."""
        assert DigestFrequency.NEVER.value == "never"
        assert DigestFrequency.IMMEDIATE.value == "immediate"
        assert DigestFrequency.DAILY.value == "daily"
        assert DigestFrequency.WEEKLY.value == "weekly"


class TestNotificationPreference:
    """Tests for NotificationPreference model."""

    def test_preference_defaults(self):
        """Test preference default values."""
        pref = NotificationPreference(
            user_id=1,
            category=NotificationCategory.CONTENT,
        )

        assert pref.email_enabled is True
        assert pref.in_app_enabled is True
        assert pref.push_enabled is False
        assert pref.sms_enabled is False
        assert pref.digest_frequency == DigestFrequency.IMMEDIATE


class TestNotificationTemplate:
    """Tests for NotificationTemplate model."""

    def test_template_creation(self):
        """Test creating a notification template."""
        template = NotificationTemplate(
            name="welcome_email",
            category=NotificationCategory.SYSTEM,
            subject="Welcome to CMS",
            body_text="Hello {{username}}, welcome to our CMS!",
        )

        assert template.name == "welcome_email"
        assert template.is_active is True


class TestNotificationRoutes:
    """Tests for notification endpoints."""

    @pytest.mark.asyncio
    async def test_get_notifications_requires_auth(self):
        """Test that getting notifications requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/notifications")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_unread_count_requires_auth(self):
        """Test that getting unread count requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/notifications/unread-count")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_preferences_requires_auth(self):
        """Test that getting preferences requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/notifications/preferences")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_categories(self):
        """Test listing notification categories."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/notifications/categories")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0

        # Check structure
        category = data["categories"][0]
        assert "value" in category
        assert "name" in category

    @pytest.mark.asyncio
    async def test_list_digest_frequencies(self):
        """Test listing digest frequencies."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/notifications/digest-frequencies")

        assert response.status_code == 200
        data = response.json()
        assert "frequencies" in data
        assert len(data["frequencies"]) > 0

    @pytest.mark.asyncio
    async def test_update_preference_requires_auth(self):
        """Test that updating preferences requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/v1/notifications/preferences/content",
                json={"email_enabled": False},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_mark_read_requires_auth(self):
        """Test that marking notification read requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/notifications/1/read")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_templates_requires_auth(self):
        """Test that listing templates requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/notifications/templates")

        assert response.status_code == 401


class TestNotificationEmailIntegration:
    """Tests for notification service email integration."""

    def test_email_service_import(self):
        """Test that email_service is imported in notification_service."""
        from app.services.notification_service import email_service

        assert email_service is not None

    def test_notification_service_has_process_immediate_queue(self):
        """Test that NotificationService has process_immediate_queue method."""
        from app.services.notification_service import NotificationService

        assert hasattr(NotificationService, "process_immediate_queue")
        assert callable(NotificationService.process_immediate_queue)

    def test_notification_service_has_send_digest(self):
        """Test that NotificationService has _send_digest method."""
        from app.services.notification_service import NotificationService

        assert hasattr(NotificationService, "_send_digest")
        assert callable(NotificationService._send_digest)

    def test_notification_service_has_queue_email(self):
        """Test that NotificationService has _queue_email method."""
        from app.services.notification_service import NotificationService

        assert hasattr(NotificationService, "_queue_email")
        assert callable(NotificationService._queue_email)
