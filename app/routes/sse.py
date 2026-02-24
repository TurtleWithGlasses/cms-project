"""
SSE (Server-Sent Events) Routes — Phase 6.4 Real-Time Features

Endpoints:
    GET /api/v1/sse/events    — full event stream (auth required)
    GET /api/v1/sse/activity  — activity feed stream (auth required)

Both endpoints use standard StreamingResponse with media_type="text/event-stream".
No extra packages required (FastAPI/Starlette built-in).

Event format (one per line-pair):
    data: {"type": "...", "data": {...}, "timestamp": "..."}\n\n

Keepalive comment (every sse_keepalive_interval seconds while idle):
    : keepalive\n\n
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.config import settings
from app.models.user import User  # noqa: TC001
from app.services.sse_manager import SSEBroadcaster, get_sse_broadcaster

router = APIRouter(tags=["Server-Sent Events"])
logger = logging.getLogger(__name__)


# ── Shared streaming helper ───────────────────────────────────────────────────


async def _event_stream(request: Request, broadcaster: SSEBroadcaster):
    """Async generator that yields SSE-formatted strings.

    Subscribes to the broadcaster, yields events as they arrive, and sends
    a keepalive comment every ``sse_keepalive_interval`` seconds so proxies
    and clients don't close the connection due to inactivity.

    Unsubscribes automatically on client disconnect or generator exhaustion.
    """
    queue = await broadcaster.subscribe()
    try:
        # Send an initial "connected" event so the client knows the stream is live
        connected_payload = json.dumps(
            {
                "type": "connected",
                "data": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        yield f"data: {connected_payload}\n\n"

        while True:
            if await request.is_disconnected():
                logger.debug("SSE client disconnected")
                break

            try:
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=float(settings.sse_keepalive_interval),
                )
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive so the connection stays open through proxies
                yield ": keepalive\n\n"

    finally:
        await broadcaster.unsubscribe(queue)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/events")
async def sse_events(
    request: Request,
    _current_user: User = Depends(get_current_user),
    broadcaster: SSEBroadcaster = Depends(get_sse_broadcaster),
) -> StreamingResponse:
    """
    Full real-time event stream (auth required).

    Streams all content and comment events published by the CMS in real time.

    **Event types**:
    - ``connected``           — initial handshake
    - ``content.created``     — new content item created
    - ``content.updated``     — content item updated
    - ``content.deleted``     — content item deleted
    - ``content.published``   — content item published
    - ``comment.created``     — new comment posted
    - ``comment.approved``    — comment approved by moderator
    - ``comment.deleted``     — comment deleted

    **Client-side example** (JavaScript):
    ```javascript
    const evtSrc = new EventSource('/api/v1/sse/events', { withCredentials: true });
    evtSrc.onmessage = (e) => {
        const event = JSON.parse(e.data);
        console.log(event.type, event.data);
    };
    ```

    Connect via `Authorization: Bearer <token>` header or `access_token` cookie.
    """
    return StreamingResponse(
        _event_stream(request, broadcaster),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering for SSE
        },
    )


@router.get("/activity")
async def sse_activity(
    request: Request,
    _current_user: User = Depends(get_current_user),
    broadcaster: SSEBroadcaster = Depends(get_sse_broadcaster),
) -> StreamingResponse:
    """
    Activity feed event stream (auth required).

    Identical to ``/events`` but semantically scoped for the admin activity
    feed widget.  Both endpoints share the same broadcaster so they receive
    the same events.

    Connect via `Authorization: Bearer <token>` header or `access_token` cookie.
    """
    return StreamingResponse(
        _event_stream(request, broadcaster),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
