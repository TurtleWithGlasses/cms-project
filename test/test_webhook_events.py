"""
Tests for Phase 4.1: Webhook event wiring and new pause/resume endpoints.
"""

import inspect

import pytest

from app.services.webhook_service import WebhookEventDispatcher, WebhookService

# ============================================================================
# TestWebhookDispatcher — dispatcher method coverage
# ============================================================================


class TestWebhookDispatcher:
    def test_comment_approved_method_exists(self):
        assert hasattr(WebhookEventDispatcher, "comment_approved")

    def test_comment_approved_is_coroutine(self):
        assert inspect.iscoroutinefunction(WebhookEventDispatcher.comment_approved)

    def test_all_content_dispatcher_methods_exist(self):
        for method in ("content_created", "content_updated", "content_published", "content_deleted"):
            assert hasattr(WebhookEventDispatcher, method), f"Missing: {method}"

    def test_all_dispatcher_methods_are_coroutines(self):
        for method in (
            "content_created",
            "content_updated",
            "content_published",
            "content_deleted",
            "comment_created",
            "comment_approved",
            "user_created",
            "media_uploaded",
        ):
            fn = getattr(WebhookEventDispatcher, method)
            assert inspect.iscoroutinefunction(fn), f"{method} must be a coroutine"


# ============================================================================
# TestWebhookPauseResume — service methods + route registration
# ============================================================================


class TestWebhookPauseResume:
    def test_pause_webhook_method_exists(self):
        assert hasattr(WebhookService, "pause_webhook")

    def test_resume_webhook_method_exists(self):
        assert hasattr(WebhookService, "resume_webhook")

    def test_pause_webhook_is_coroutine(self):
        assert inspect.iscoroutinefunction(WebhookService.pause_webhook)

    def test_resume_webhook_is_coroutine(self):
        assert inspect.iscoroutinefunction(WebhookService.resume_webhook)

    def test_pause_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("pause" in p for p in paths), f"No pause route found in: {paths}"

    def test_resume_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("resume" in p for p in paths), f"No resume route found in: {paths}"

    def test_pause_route_requires_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        response = client.post("/api/v1/webhooks/1/pause")
        assert response.status_code in (307, 401, 403)

    def test_resume_route_requires_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        response = client.post("/api/v1/webhooks/1/resume")
        assert response.status_code in (307, 401, 403)


# ============================================================================
# TestWebhookEventWiring — verify route modules import the dispatcher
# ============================================================================


class TestWebhookEventWiring:
    def test_content_routes_import_dispatcher(self):
        import app.routes.content as content_module

        assert hasattr(content_module, "WebhookEventDispatcher"), "content.py must import WebhookEventDispatcher"

    def test_comments_routes_import_dispatcher(self):
        import app.routes.comments as comments_module

        assert hasattr(comments_module, "WebhookEventDispatcher"), "comments.py must import WebhookEventDispatcher"

    def test_media_routes_import_dispatcher(self):
        import app.routes.media as media_module

        assert hasattr(media_module, "WebhookEventDispatcher"), "media.py must import WebhookEventDispatcher"

    def test_content_routes_use_asyncio(self):
        import app.routes.content as content_module

        assert hasattr(content_module, "asyncio"), "content.py must import asyncio for create_task"

    def test_comments_routes_use_asyncio(self):
        import app.routes.comments as comments_module

        assert hasattr(comments_module, "asyncio"), "comments.py must import asyncio for create_task"

    def test_media_routes_use_asyncio(self):
        import app.routes.media as media_module

        assert hasattr(media_module, "asyncio"), "media.py must import asyncio for create_task"

    def test_webhook_service_has_pause_and_resume(self):
        """Verifies the service layer supports pause/resume."""
        from app.services.webhook_service import WebhookService

        assert hasattr(WebhookService, "pause_webhook")
        assert hasattr(WebhookService, "resume_webhook")
