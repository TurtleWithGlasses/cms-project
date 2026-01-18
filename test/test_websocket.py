"""
Tests for WebSocket functionality.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.websocket_manager import (
    MessageType,
    WebSocketConnection,
    WebSocketManager,
    get_websocket_manager,
)
from main import app


class TestMessageTypes:
    """Tests for WebSocket message types."""

    def test_system_messages(self):
        """Test system message types."""
        assert MessageType.CONNECTED.value == "connected"
        assert MessageType.DISCONNECTED.value == "disconnected"
        assert MessageType.HEARTBEAT.value == "heartbeat"
        assert MessageType.ERROR.value == "error"

    def test_content_messages(self):
        """Test content event message types."""
        assert MessageType.CONTENT_CREATED.value == "content.created"
        assert MessageType.CONTENT_UPDATED.value == "content.updated"
        assert MessageType.CONTENT_DELETED.value == "content.deleted"
        assert MessageType.CONTENT_PUBLISHED.value == "content.published"

    def test_comment_messages(self):
        """Test comment event message types."""
        assert MessageType.COMMENT_CREATED.value == "comment.created"
        assert MessageType.COMMENT_APPROVED.value == "comment.approved"
        assert MessageType.COMMENT_DELETED.value == "comment.deleted"

    def test_notification_message(self):
        """Test notification message type."""
        assert MessageType.NOTIFICATION.value == "notification"


class TestWebSocketManager:
    """Tests for WebSocket manager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh WebSocket manager for testing."""
        return WebSocketManager()

    def test_initial_state(self, manager):
        """Test initial manager state."""
        stats = manager.get_stats()

        assert stats["total_connections"] == 0
        assert stats["unique_users"] == 0
        assert stats["channels"] == 0

    def test_get_singleton(self):
        """Test singleton instance."""
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()

        assert manager1 is manager2


class TestWebSocketConnection:
    """Tests for WebSocket connection dataclass."""

    def test_connection_defaults(self):
        """Test connection default values."""
        # Can't create without websocket, but we can test the structure
        from datetime import datetime, timezone
        from unittest.mock import MagicMock

        mock_ws = MagicMock()
        connection = WebSocketConnection(
            websocket=mock_ws,
            user_id=1,
        )

        assert connection.user_id == 1
        assert connection.subscriptions == set()
        assert connection.connected_at is not None
        assert connection.last_heartbeat is not None

    def test_connection_with_user(self):
        """Test connection with user ID."""
        from unittest.mock import MagicMock

        mock_ws = MagicMock()
        connection = WebSocketConnection(
            websocket=mock_ws,
            user_id=42,
        )

        assert connection.user_id == 42

    def test_connection_without_user(self):
        """Test anonymous connection."""
        from unittest.mock import MagicMock

        mock_ws = MagicMock()
        connection = WebSocketConnection(
            websocket=mock_ws,
            user_id=None,
        )

        assert connection.user_id is None


class TestWebSocketRoutes:
    """Tests for WebSocket HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting WebSocket stats."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/ws/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_connections" in data
        assert "unique_users" in data
        assert "channels" in data

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """Test broadcast endpoint."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/ws/broadcast",
                params={
                    "message_type": "notification",
                    "message": "Test broadcast",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert "sent_to" in data
        assert "message" in data

    @pytest.mark.asyncio
    async def test_send_to_user(self):
        """Test send to user endpoint."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/ws/send-to-user/1",
                params={
                    "message_type": "notification",
                    "message": "Test message",
                },
            )

        assert response.status_code == 200
        data = response.json()

        assert "sent_to" in data
        # Should be 0 since no user is connected
        assert data["sent_to"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_connections(self):
        """Test cleanup endpoint."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/ws/cleanup",
                params={"timeout_seconds": 60},
            )

        assert response.status_code == 200
        data = response.json()

        assert "cleaned" in data
        assert "message" in data


class TestMessageHandling:
    """Tests for WebSocket message handling."""

    @pytest.fixture
    def manager(self):
        """Create a fresh WebSocket manager for testing."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_handle_ping_message(self, manager):
        """Test handling ping message."""
        response = await manager.handle_message(
            "test_connection",
            {"type": "ping"},
        )

        assert response is not None
        assert response["type"] == "pong"
        assert "timestamp" in response

    @pytest.mark.asyncio
    async def test_handle_heartbeat_message(self, manager):
        """Test handling heartbeat message."""
        response = await manager.handle_message(
            "test_connection",
            {"type": "heartbeat"},
        )

        assert response is not None
        assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, manager):
        """Test handling subscribe message."""
        response = await manager.handle_message(
            "test_connection",
            {"type": "subscribe", "channel": "content"},
        )

        # Since connection doesn't exist, should return error
        assert response is not None
        assert response["type"] in ["subscribed", "error"]

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_message(self, manager):
        """Test handling unsubscribe message."""
        response = await manager.handle_message(
            "test_connection",
            {"type": "unsubscribe", "channel": "content"},
        )

        # Since connection doesn't exist, should return error
        assert response is not None
        assert response["type"] in ["unsubscribed", "error"]
