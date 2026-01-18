"""
WebSocket Manager

Manages WebSocket connections for real-time notifications.
Supports user-specific and broadcast messaging.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""

    # System messages
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

    # Content events
    CONTENT_CREATED = "content.created"
    CONTENT_UPDATED = "content.updated"
    CONTENT_DELETED = "content.deleted"
    CONTENT_PUBLISHED = "content.published"

    # Comment events
    COMMENT_CREATED = "comment.created"
    COMMENT_APPROVED = "comment.approved"
    COMMENT_DELETED = "comment.deleted"

    # Notification events
    NOTIFICATION = "notification"

    # User events
    USER_UPDATED = "user.updated"


@dataclass
class WebSocketConnection:
    """Represents an active WebSocket connection."""

    websocket: WebSocket
    user_id: int | None
    subscriptions: set = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.

    Features:
    - User-specific connections
    - Channel subscriptions
    - Broadcast messaging
    - Heartbeat monitoring
    - Automatic cleanup
    """

    def __init__(self):
        # Connection storage
        self._connections: dict[str, WebSocketConnection] = {}

        # User to connections mapping (one user can have multiple connections)
        self._user_connections: dict[int, set[str]] = defaultdict(set)

        # Channel subscriptions
        self._channel_subscribers: dict[str, set[str]] = defaultdict(set)

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int | None = None,
        connection_id: str | None = None,
    ) -> str:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket instance
            user_id: Optional user ID for authenticated connections
            connection_id: Optional custom connection ID

        Returns:
            Connection ID
        """
        await websocket.accept()

        # Generate connection ID if not provided
        if not connection_id:
            import uuid

            connection_id = str(uuid.uuid4())

        async with self._lock:
            # Store connection
            connection = WebSocketConnection(
                websocket=websocket,
                user_id=user_id,
            )
            self._connections[connection_id] = connection

            # Track user connection
            if user_id:
                self._user_connections[user_id].add(connection_id)

        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")

        # Send welcome message
        await self._send_to_connection(
            connection_id,
            {
                "type": MessageType.CONNECTED.value,
                "connection_id": connection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            connection_id: The connection ID to remove
        """
        async with self._lock:
            connection = self._connections.pop(connection_id, None)

            if connection:
                # Remove from user connections
                if connection.user_id:
                    self._user_connections[connection.user_id].discard(connection_id)
                    if not self._user_connections[connection.user_id]:
                        del self._user_connections[connection.user_id]

                # Remove from all channels
                for channel in connection.subscriptions:
                    self._channel_subscribers[channel].discard(connection_id)

                logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe(self, connection_id: str, channel: str) -> bool:
        """
        Subscribe a connection to a channel.

        Args:
            connection_id: The connection ID
            channel: Channel name to subscribe to

        Returns:
            True if subscribed successfully
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False

            connection.subscriptions.add(channel)
            self._channel_subscribers[channel].add(connection_id)

        logger.debug(f"Connection {connection_id} subscribed to {channel}")
        return True

    async def unsubscribe(self, connection_id: str, channel: str) -> bool:
        """
        Unsubscribe a connection from a channel.

        Args:
            connection_id: The connection ID
            channel: Channel name to unsubscribe from

        Returns:
            True if unsubscribed successfully
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False

            connection.subscriptions.discard(channel)
            self._channel_subscribers[channel].discard(connection_id)

        logger.debug(f"Connection {connection_id} unsubscribed from {channel}")
        return True

    async def send_to_user(
        self,
        user_id: int,
        message_type: str,
        data: dict,
    ) -> int:
        """
        Send a message to all connections of a specific user.

        Args:
            user_id: Target user ID
            message_type: Type of message
            data: Message payload

        Returns:
            Number of connections the message was sent to
        """
        message = self._create_message(message_type, data)
        connection_ids = self._user_connections.get(user_id, set()).copy()

        sent_count = 0
        for connection_id in connection_ids:
            if await self._send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def send_to_channel(
        self,
        channel: str,
        message_type: str,
        data: dict,
    ) -> int:
        """
        Send a message to all subscribers of a channel.

        Args:
            channel: Target channel name
            message_type: Type of message
            data: Message payload

        Returns:
            Number of connections the message was sent to
        """
        message = self._create_message(message_type, data)
        connection_ids = self._channel_subscribers.get(channel, set()).copy()

        sent_count = 0
        for connection_id in connection_ids:
            if await self._send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def broadcast(
        self,
        message_type: str,
        data: dict,
        exclude_user_ids: list[int] | None = None,
    ) -> int:
        """
        Broadcast a message to all connected clients.

        Args:
            message_type: Type of message
            data: Message payload
            exclude_user_ids: User IDs to exclude from broadcast

        Returns:
            Number of connections the message was sent to
        """
        message = self._create_message(message_type, data)
        exclude_user_ids = exclude_user_ids or []

        sent_count = 0
        async with self._lock:
            connection_ids = list(self._connections.keys())

        for connection_id in connection_ids:
            connection = self._connections.get(connection_id)
            if (
                connection
                and connection.user_id not in exclude_user_ids
                and await self._send_to_connection(connection_id, message)
            ):
                sent_count += 1

        return sent_count

    async def handle_message(
        self,
        connection_id: str,
        message: dict,
    ) -> dict | None:
        """
        Handle an incoming WebSocket message.

        Args:
            connection_id: The connection ID
            message: The received message

        Returns:
            Response message or None
        """
        msg_type = message.get("type", "unknown")

        # Handle heartbeat
        if msg_type == "heartbeat" or msg_type == "ping":
            async with self._lock:
                connection = self._connections.get(connection_id)
                if connection:
                    connection.last_heartbeat = datetime.now(timezone.utc)
            return {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}

        # Handle subscription
        if msg_type == "subscribe":
            channel = message.get("channel")
            if channel:
                success = await self.subscribe(connection_id, channel)
                return {
                    "type": "subscribed" if success else "error",
                    "channel": channel,
                }

        # Handle unsubscription
        if msg_type == "unsubscribe":
            channel = message.get("channel")
            if channel:
                success = await self.unsubscribe(connection_id, channel)
                return {
                    "type": "unsubscribed" if success else "error",
                    "channel": channel,
                }

        return None

    async def get_connection_info(self, connection_id: str) -> dict | None:
        """Get information about a connection."""
        connection = self._connections.get(connection_id)
        if not connection:
            return None

        return {
            "connection_id": connection_id,
            "user_id": connection.user_id,
            "subscriptions": list(connection.subscriptions),
            "connected_at": connection.connected_at.isoformat(),
            "last_heartbeat": connection.last_heartbeat.isoformat(),
        }

    def get_stats(self) -> dict:
        """Get WebSocket manager statistics."""
        return {
            "total_connections": len(self._connections),
            "unique_users": len(self._user_connections),
            "channels": len(self._channel_subscribers),
            "channel_stats": {channel: len(subscribers) for channel, subscribers in self._channel_subscribers.items()},
        }

    async def cleanup_stale_connections(self, timeout_seconds: int = 60) -> int:
        """
        Remove stale connections that haven't sent heartbeats.

        Args:
            timeout_seconds: Seconds without heartbeat before considered stale

        Returns:
            Number of connections cleaned up
        """
        now = datetime.now(timezone.utc)
        stale_ids = []

        async with self._lock:
            for conn_id, connection in self._connections.items():
                elapsed = (now - connection.last_heartbeat).total_seconds()
                if elapsed > timeout_seconds:
                    stale_ids.append(conn_id)

        for conn_id in stale_ids:
            await self.disconnect(conn_id)

        if stale_ids:
            logger.info(f"Cleaned up {len(stale_ids)} stale connections")

        return len(stale_ids)

    # ============== Private Methods ==============

    def _create_message(self, message_type: str, data: dict) -> dict:
        """Create a standardized message envelope."""
        return {
            "type": message_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _send_to_connection(
        self,
        connection_id: str,
        message: dict,
    ) -> bool:
        """
        Send a message to a specific connection.

        Returns:
            True if sent successfully
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False

        try:
            await connection.websocket.send_json(message)
            return True
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to {connection_id}: {e}")
            return False


# ============== Global Instance ==============

# Singleton instance
websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """Get the WebSocket manager singleton."""
    return websocket_manager


# ============== Event Broadcasting Helpers ==============


async def broadcast_content_event(
    event_type: str,
    content_id: int,
    title: str,
    author_id: int,
) -> None:
    """Broadcast a content-related event."""
    await websocket_manager.broadcast(
        message_type=event_type,
        data={
            "content_id": content_id,
            "title": title,
            "author_id": author_id,
        },
    )


async def broadcast_comment_event(
    event_type: str,
    comment_id: int,
    content_id: int,
    author_id: int,
) -> None:
    """Broadcast a comment-related event."""
    # Send to content channel
    await websocket_manager.send_to_channel(
        channel=f"content:{content_id}",
        message_type=event_type,
        data={
            "comment_id": comment_id,
            "content_id": content_id,
            "author_id": author_id,
        },
    )


async def send_notification_to_user(
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
    data: dict | None = None,
) -> None:
    """Send a notification to a specific user."""
    await websocket_manager.send_to_user(
        user_id=user_id,
        message_type=MessageType.NOTIFICATION.value,
        data={
            "title": title,
            "message": message,
            "notification_type": notification_type,
            **(data or {}),
        },
    )
