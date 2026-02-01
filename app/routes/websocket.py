"""
WebSocket Routes

WebSocket endpoints for real-time notifications.
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_context
from app.models.user import User
from app.services.websocket_manager import WebSocketManager, get_websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def get_user_from_token(token: str, db: AsyncSession) -> User | None:
    """Validate JWT token and return user."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        email = payload.get("sub")
        if not email:
            return None

        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    except JWTError:
        return None


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Annotated[str | None, Query()] = None,
):
    """
    WebSocket connection endpoint.

    Connect to receive real-time updates. Optionally provide a JWT token
    for authenticated connections.

    Message Types (Client -> Server):
    - ping/heartbeat: Keep connection alive
    - subscribe: Subscribe to a channel (requires channel field)
    - unsubscribe: Unsubscribe from a channel (requires channel field)

    Message Types (Server -> Client):
    - connected: Connection established
    - pong: Response to ping
    - subscribed/unsubscribed: Subscription confirmation
    - notification: User notification
    - content.created/updated/deleted/published: Content events
    - comment.created/approved/deleted: Comment events

    Example Usage:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws?token=YOUR_JWT_TOKEN');

    ws.onopen = () => {
        // Subscribe to content updates
        ws.send(JSON.stringify({type: 'subscribe', channel: 'content'}));
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received:', message.type, message.data);
    };

    // Send periodic heartbeats
    setInterval(() => {
        ws.send(JSON.stringify({type: 'ping'}));
    }, 30000);
    ```
    """
    manager = get_websocket_manager()

    # Authenticate if token provided
    user_id = None
    if token:
        async with get_db_context() as db:
            user = await get_user_from_token(token, db)
            if user:
                user_id = user.id

    # Accept connection
    connection_id = await manager.connect(websocket, user_id)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid JSON",
                    }
                )
                continue

            # Handle message
            response = await manager.handle_message(connection_id, message)

            if response:
                await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(connection_id)


@router.get("/stats")
async def get_websocket_stats(
    manager: WebSocketManager = Depends(get_websocket_manager),
) -> dict:
    """
    Get WebSocket connection statistics.

    Returns current connection counts and channel subscriptions.
    """
    return manager.get_stats()


# ============== Admin Endpoints ==============


@router.post("/broadcast")
async def broadcast_message(
    message_type: str,
    message: str,
    data: dict | None = None,
    manager: WebSocketManager = Depends(get_websocket_manager),
) -> dict:
    """
    Broadcast a message to all connected clients.

    Admin endpoint for sending system-wide notifications.
    """
    sent_count = await manager.broadcast(
        message_type=message_type,
        data={
            "message": message,
            **(data or {}),
        },
    )

    return {
        "sent_to": sent_count,
        "message": f"Broadcast sent to {sent_count} connections",
    }


@router.post("/send-to-user/{user_id}")
async def send_to_user(
    user_id: int,
    message_type: str,
    message: str,
    data: dict | None = None,
    manager: WebSocketManager = Depends(get_websocket_manager),
) -> dict:
    """
    Send a message to a specific user.

    Admin endpoint for sending targeted notifications.
    """
    sent_count = await manager.send_to_user(
        user_id=user_id,
        message_type=message_type,
        data={
            "message": message,
            **(data or {}),
        },
    )

    return {
        "sent_to": sent_count,
        "message": f"Message sent to {sent_count} connections for user {user_id}",
    }


@router.post("/cleanup")
async def cleanup_connections(
    timeout_seconds: int = 60,
    manager: WebSocketManager = Depends(get_websocket_manager),
) -> dict:
    """
    Cleanup stale WebSocket connections.

    Removes connections that haven't sent heartbeats within the timeout.
    """
    cleaned = await manager.cleanup_stale_connections(timeout_seconds)

    return {
        "cleaned": cleaned,
        "message": f"Removed {cleaned} stale connections",
    }
