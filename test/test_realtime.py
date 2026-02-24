"""
Tests for Phase 6.4 Real-Time Features — WebSocket fixes, SSE, and user presence.

All tests run without a live database or Redis connection.

Test classes:
    TestSSEManager          — SSEBroadcaster unit tests
    TestSSERoutes           — SSE endpoint registration + auth
    TestWebSocketPresence   — presence tracking additions
    TestWebSocketFixes      — bug-fix verification (config attrs, route prefix)
    TestRealtimeConfig      — settings additions
    TestWebSocketRoutesFull — public HTTP endpoints now return 200
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, settings
from app.services.sse_manager import SSEBroadcaster, get_sse_broadcaster, sse_broadcaster
from app.services.websocket_manager import (
    MessageType,
    WebSocketManager,
    broadcast_comment_event,
    broadcast_content_event,
    get_websocket_manager,
    send_notification_to_user,
)
from main import app

# ── TestSSEManager ────────────────────────────────────────────────────────────


class TestSSEManager:
    """Unit tests for SSEBroadcaster."""

    @pytest.fixture
    def broadcaster(self):
        return SSEBroadcaster(max_queue_size=10)

    @pytest.mark.asyncio
    async def test_subscribe_returns_queue(self, broadcaster):
        q = await broadcaster.subscribe()
        assert isinstance(q, asyncio.Queue)
        await broadcaster.unsubscribe(q)

    @pytest.mark.asyncio
    async def test_subscribe_increments_count(self, broadcaster):
        assert broadcaster.subscriber_count() == 0
        q = await broadcaster.subscribe()
        assert broadcaster.subscriber_count() == 1
        await broadcaster.unsubscribe(q)
        assert broadcaster.subscriber_count() == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_idempotent(self, broadcaster):
        """Unsubscribing an already-removed queue should not raise."""
        q = await broadcaster.subscribe()
        await broadcaster.unsubscribe(q)
        await broadcaster.unsubscribe(q)  # second call is a no-op

    @pytest.mark.asyncio
    async def test_publish_fans_out(self, broadcaster):
        q1 = await broadcaster.subscribe()
        q2 = await broadcaster.subscribe()

        count = await broadcaster.publish("test.event", {"key": "value"})

        assert count == 2
        assert not q1.empty()
        assert not q2.empty()

        payload1 = q1.get_nowait()
        payload2 = q2.get_nowait()
        assert payload1["type"] == "test.event"
        assert payload2["data"]["key"] == "value"

        await broadcaster.unsubscribe(q1)
        await broadcaster.unsubscribe(q2)

    @pytest.mark.asyncio
    async def test_publish_returns_zero_when_no_listeners(self, broadcaster):
        count = await broadcaster.publish("content.published", {"id": 1})
        assert count == 0

    @pytest.mark.asyncio
    async def test_publish_drops_event_for_full_queue(self, broadcaster):
        """Full queues should silently drop events (non-blocking)."""
        q = await broadcaster.subscribe()
        # Fill the queue to capacity
        for i in range(10):
            await broadcaster.publish("fill", {"i": i})

        # One more publish — should not raise, just drop
        count = await broadcaster.publish("overflow", {"x": 1})
        assert count == 0  # dropped because full

        await broadcaster.unsubscribe(q)

    @pytest.mark.asyncio
    async def test_publish_payload_includes_timestamp(self, broadcaster):
        q = await broadcaster.subscribe()
        await broadcaster.publish("x", {})
        payload = q.get_nowait()
        assert "timestamp" in payload
        await broadcaster.unsubscribe(q)

    @pytest.mark.asyncio
    async def test_multiple_subscribes_same_broadcaster(self, broadcaster):
        queues = [await broadcaster.subscribe() for _ in range(5)]
        assert broadcaster.subscriber_count() == 5
        for q in queues:
            await broadcaster.unsubscribe(q)
        assert broadcaster.subscriber_count() == 0

    def test_subscriber_count_initially_zero(self, broadcaster):
        assert broadcaster.subscriber_count() == 0

    def test_get_sse_broadcaster_returns_singleton(self):
        b1 = get_sse_broadcaster()
        b2 = get_sse_broadcaster()
        assert b1 is b2

    def test_module_singleton_is_sse_broadcaster_instance(self):
        assert isinstance(sse_broadcaster, SSEBroadcaster)

    @pytest.mark.asyncio
    async def test_publish_only_reaches_active_queues(self, broadcaster):
        q1 = await broadcaster.subscribe()
        q2 = await broadcaster.subscribe()
        await broadcaster.unsubscribe(q2)

        count = await broadcaster.publish("event", {"a": 1})
        assert count == 1

        await broadcaster.unsubscribe(q1)


# ── TestSSERoutes ─────────────────────────────────────────────────────────────


class TestSSERoutes:
    """SSE endpoint registration and auth tests."""

    def test_sse_events_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/sse/events" in paths

    def test_sse_activity_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/sse/activity" in paths

    def test_sse_router_tag(self):
        from app.routes.sse import router as sse_router

        assert "Server-Sent Events" in sse_router.tags

    @pytest.mark.asyncio
    async def test_sse_events_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.get("/api/v1/sse/events")
        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_sse_activity_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.get("/api/v1/sse/activity")
        assert response.status_code in (307, 401, 403)

    def test_sse_manager_importable(self):
        from app.services.sse_manager import SSEBroadcaster, get_sse_broadcaster

        assert SSEBroadcaster is not None
        assert callable(get_sse_broadcaster)

    def test_sse_route_module_importable(self):
        from app.routes.sse import router

        assert router is not None

    def test_both_endpoints_are_get(self):
        from app.routes.sse import router

        methods = {route.path: list(route.methods) for route in router.routes if hasattr(route, "methods")}
        assert "GET" in methods.get("/events", [])
        assert "GET" in methods.get("/activity", [])


# ── TestWebSocketPresence ─────────────────────────────────────────────────────


class TestWebSocketPresence:
    """Tests for live user presence additions."""

    def test_user_online_in_message_type(self):
        assert MessageType.USER_ONLINE.value == "user.online"

    def test_user_offline_in_message_type(self):
        assert MessageType.USER_OFFLINE.value == "user.offline"

    def test_get_online_user_ids_exists(self):
        manager = WebSocketManager()
        result = manager.get_online_user_ids()
        assert isinstance(result, list)

    def test_get_online_user_ids_empty_initially(self):
        manager = WebSocketManager()
        assert manager.get_online_user_ids() == []

    def test_presence_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/ws/presence" in paths

    @pytest.mark.asyncio
    async def test_presence_endpoint_is_public(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/ws/presence")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_presence_response_has_online_users_key(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/ws/presence")
        data = response.json()
        assert "online_users" in data
        assert "count" in data

    @pytest.mark.asyncio
    async def test_presence_count_is_int(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/ws/presence")
        assert isinstance(response.json()["count"], int)


# ── TestWebSocketFixes ────────────────────────────────────────────────────────


class TestWebSocketFixes:
    """Verify bug fixes: correct config attribute names, route prefix."""

    def test_constants_importable(self):
        from app.constants import ALGORITHM, SECRET_KEY

        assert SECRET_KEY is not None
        assert ALGORITHM is not None

    def test_secret_key_matches_settings(self):
        from app.constants import SECRET_KEY

        assert settings.secret_key == SECRET_KEY

    def test_algorithm_is_hs256(self):
        from app.constants import ALGORITHM

        assert ALGORITHM == "HS256"

    def test_broadcast_content_event_is_coroutine(self):
        import inspect

        assert inspect.iscoroutinefunction(broadcast_content_event)

    def test_broadcast_comment_event_is_coroutine(self):
        import inspect

        assert inspect.iscoroutinefunction(broadcast_comment_event)

    def test_send_notification_to_user_is_coroutine(self):
        import inspect

        assert inspect.iscoroutinefunction(send_notification_to_user)

    def test_websocket_manager_singleton(self):
        m1 = get_websocket_manager()
        m2 = get_websocket_manager()
        assert m1 is m2

    def test_ws_stats_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/ws/stats" in paths

    def test_ws_presence_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/ws/presence" in paths

    def test_get_online_user_ids_returns_sorted_list(self):
        manager = WebSocketManager()
        # No connections → empty list
        result = manager.get_online_user_ids()
        assert result == sorted(result)


# ── TestRealtimeConfig ────────────────────────────────────────────────────────


class TestRealtimeConfig:
    """Phase 6.4 config additions."""

    def test_version_bumped_to_1_23_0(self):
        default = Settings.model_fields["app_version"].default
        assert default == "1.23.0"

    def test_sse_keepalive_interval_exists(self):
        assert hasattr(settings, "sse_keepalive_interval")

    def test_sse_keepalive_interval_positive(self):
        assert settings.sse_keepalive_interval >= 1

    def test_sse_max_queue_size_exists(self):
        assert hasattr(settings, "sse_max_queue_size")

    def test_sse_max_queue_size_reasonable(self):
        assert settings.sse_max_queue_size >= 10


# ── TestWebSocketRoutesFull ───────────────────────────────────────────────────


class TestWebSocketRoutesFull:
    """Public WebSocket HTTP endpoints return 200 after fixes."""

    @pytest.mark.asyncio
    async def test_ws_stats_is_public(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/ws/stats")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ws_stats_response_keys(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/ws/stats")
        data = response.json()
        assert "total_connections" in data
        assert "unique_users" in data
        assert "channels" in data

    @pytest.mark.asyncio
    async def test_ws_presence_is_public(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/ws/presence")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ws_presence_response_keys(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/ws/presence")
        data = response.json()
        assert "online_users" in data
        assert isinstance(data["online_users"], list)
        assert "count" in data

    @pytest.mark.asyncio
    async def test_ws_broadcast_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.post(
                "/api/v1/ws/broadcast",
                params={"message_type": "test", "message": "hi"},
            )
        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_ws_send_to_user_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.post(
                "/api/v1/ws/send-to-user/1",
                params={"message_type": "test", "message": "hi"},
            )
        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_ws_cleanup_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.post(
                "/api/v1/ws/cleanup",
                params={"timeout_seconds": 60},
            )
        assert response.status_code in (307, 401, 403)
