"""
SSE (Server-Sent Events) Manager — Phase 6.4 Real-Time Features

Manages a fan-out broadcaster for SSE listeners.  Each connected SSE client
gets its own asyncio.Queue; when an event is published every queue receives
a copy of the payload.

Classes:
    SSEBroadcaster  — subscribe / unsubscribe / publish

Module-level singleton:
    sse_broadcaster         — shared instance
    get_sse_broadcaster()   — getter (dependency-injection friendly)
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SSEBroadcaster:
    """
    Fan-out broadcaster for Server-Sent Events listeners.

    Each subscriber gets an asyncio.Queue with a fixed capacity.  If the
    queue is full when a new event arrives the event is silently dropped for
    that slow consumer only (non-blocking).
    """

    def __init__(self, max_queue_size: int = 100) -> None:
        self._queues: list[asyncio.Queue] = []
        self._lock: asyncio.Lock = asyncio.Lock()
        self._max_queue_size = max_queue_size

    # ── Public API ────────────────────────────────────────────────────────────

    async def subscribe(self) -> asyncio.Queue:
        """Create and register a new listener queue.

        Returns the queue — the caller should read from it inside their
        SSE generator and call ``unsubscribe`` in a ``finally`` block.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue_size)
        async with self._lock:
            self._queues.append(queue)
        logger.debug("SSE subscriber added (total: %d)", len(self._queues))
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a listener queue."""
        async with self._lock:
            try:
                self._queues.remove(queue)
                logger.debug("SSE subscriber removed (total: %d)", len(self._queues))
            except ValueError:
                pass  # Already removed

    async def publish(self, event_type: str, data: dict) -> int:
        """Fan-out an event to all active listeners.

        Args:
            event_type: Event type string (e.g. "content.published").
            data:       Arbitrary payload dict.

        Returns:
            Number of queues that received the event.
        """
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        async with self._lock:
            queues = list(self._queues)

        delivered = 0
        for queue in queues:
            try:
                queue.put_nowait(payload)
                delivered += 1
            except asyncio.QueueFull:
                logger.warning("SSE queue full — dropping event '%s' for slow consumer", event_type)

        return delivered

    def subscriber_count(self) -> int:
        """Return the current number of active SSE listeners."""
        return len(self._queues)


# ── Module-level singleton ────────────────────────────────────────────────────

sse_broadcaster = SSEBroadcaster()


def get_sse_broadcaster() -> SSEBroadcaster:
    """Return the global SSEBroadcaster singleton."""
    return sse_broadcaster
