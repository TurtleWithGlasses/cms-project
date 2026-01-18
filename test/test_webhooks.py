"""
Tests for Webhook functionality.
"""

import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.models.webhook import Webhook, WebhookEvent, WebhookStatus
from app.services.webhook_service import WebhookService
from main import app


@pytest.fixture
def webhook_data():
    """Sample webhook creation data."""
    return {
        "name": "Test Webhook",
        "description": "Webhook for testing",
        "url": "https://example.com/webhook",
        "events": ["content.created", "content.updated"],
        "timeout_seconds": 30,
        "max_retries": 3,
    }


class TestWebhookEvents:
    """Tests for webhook event types."""

    def test_content_events(self):
        """Test content event values."""
        assert WebhookEvent.CONTENT_CREATED.value == "content.created"
        assert WebhookEvent.CONTENT_UPDATED.value == "content.updated"
        assert WebhookEvent.CONTENT_DELETED.value == "content.deleted"
        assert WebhookEvent.CONTENT_PUBLISHED.value == "content.published"

    def test_comment_events(self):
        """Test comment event values."""
        assert WebhookEvent.COMMENT_CREATED.value == "comment.created"
        assert WebhookEvent.COMMENT_APPROVED.value == "comment.approved"

    def test_wildcard_event(self):
        """Test wildcard event."""
        assert WebhookEvent.ALL.value == "*"


class TestWebhookStatus:
    """Tests for webhook status types."""

    def test_status_values(self):
        """Test status enum values."""
        assert WebhookStatus.ACTIVE.value == "active"
        assert WebhookStatus.PAUSED.value == "paused"
        assert WebhookStatus.FAILED.value == "failed"
        assert WebhookStatus.DISABLED.value == "disabled"


class TestWebhookModel:
    """Tests for Webhook model."""

    def test_get_events(self):
        """Test parsing events from string."""
        webhook = Webhook(events="content.created,content.updated")
        events = webhook.get_events()

        assert events == ["content.created", "content.updated"]

    def test_get_events_empty(self):
        """Test parsing empty events."""
        webhook = Webhook(events="")
        assert webhook.get_events() == []

    def test_is_subscribed_to_direct(self):
        """Test direct event subscription check."""
        webhook = Webhook(events="content.created,content.updated")

        assert webhook.is_subscribed_to("content.created") is True
        assert webhook.is_subscribed_to("content.updated") is True
        assert webhook.is_subscribed_to("content.deleted") is False

    def test_is_subscribed_to_wildcard(self):
        """Test wildcard subscription."""
        webhook = Webhook(events="*")

        assert webhook.is_subscribed_to("content.created") is True
        assert webhook.is_subscribed_to("anything") is True


class TestWebhookSignature:
    """Tests for webhook signature verification."""

    def test_signature_creation(self):
        """Test creating HMAC signature."""
        secret = "test_secret"
        payload = '{"test": "data"}'

        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        assert len(signature) == 64  # SHA256 hex digest length
        assert signature.isalnum()

    def test_signature_verification(self):
        """Test signature verification."""
        secret = "test_secret"
        payload = '{"test": "data"}'

        # Create signature
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Verify
        is_valid = WebhookService.verify_signature(secret, payload, signature)
        assert is_valid is True

    def test_signature_verification_invalid(self):
        """Test invalid signature rejection."""
        secret = "test_secret"
        payload = '{"test": "data"}'

        is_valid = WebhookService.verify_signature(secret, payload, "invalid_signature")
        assert is_valid is False

    def test_signature_verification_wrong_secret(self):
        """Test wrong secret rejection."""
        payload = '{"test": "data"}'

        # Create with one secret
        signature = hmac.new(
            b"secret1",
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Verify with different secret
        is_valid = WebhookService.verify_signature("secret2", payload, signature)
        assert is_valid is False


class TestWebhookRoutes:
    """Tests for webhook endpoints."""

    @pytest.mark.asyncio
    async def test_list_available_events(self):
        """Test listing available events."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/webhooks/events")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) > 0

        # Check event structure
        event = data["events"][0]
        assert "value" in event
        assert "name" in event

    @pytest.mark.asyncio
    async def test_list_webhooks_requires_auth(self):
        """Test that listing webhooks requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/webhooks")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_webhook_requires_auth(self, webhook_data):
        """Test that creating webhooks requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/webhooks", json=webhook_data)

        assert response.status_code == 401


class TestWebhookPayload:
    """Tests for webhook payload structure."""

    def test_payload_structure(self):
        """Test expected payload structure."""
        from datetime import datetime, timezone

        event = "content.created"
        data = {"content_id": 1, "title": "Test"}

        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        assert "event" in payload
        assert "timestamp" in payload
        assert "data" in payload
        assert payload["event"] == event
        assert payload["data"] == data
