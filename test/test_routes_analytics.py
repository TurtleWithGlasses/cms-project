"""
Tests for Analytics Routes

Tests API endpoints for analytics and reporting.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from utils.mock_utils import create_test_content

from app.models.content import ContentStatus
from app.models.media import Media
from app.utils.activity_log import log_activity


class TestAnalyticsRoutes:
    """Test analytics API endpoints"""

    @pytest.mark.asyncio
    async def test_get_dashboard_overview_admin(self, client, admin_user):
        """Test admin can access dashboard overview"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/analytics/dashboard", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "users" in data
        assert "activity" in data
        assert "media" in data
        assert "generated_at" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_overview_forbidden(self, client, auth_headers):
        """Test regular user cannot access dashboard"""
        response = client.get("/api/v1/analytics/dashboard", headers=auth_headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_dashboard_overview_manager(self, client, manager_user):
        """Test manager can access dashboard"""
        from app.auth import create_access_token

        manager_token = create_access_token({"sub": manager_user.email})
        headers = {"Authorization": f"Bearer {manager_token}"}

        response = client.get("/api/v1/analytics/dashboard", headers=headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_content_statistics_admin(self, client, async_db_session, admin_user):
        """Test admin can access content statistics"""
        from app.auth import create_access_token

        # Create test content
        await create_test_content(
            async_db_session,
            title="Stats Test",
            body="Content",
            author_id=admin_user.id,
        )

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/analytics/content", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_content" in data
        assert "content_by_status" in data
        assert "recent_content_30_days" in data
        assert "content_by_category_top10" in data

    @pytest.mark.asyncio
    async def test_get_content_statistics_forbidden(self, client, auth_headers):
        """Test regular user cannot access content statistics"""
        response = client.get("/api/v1/analytics/content", headers=auth_headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user_statistics_admin(self, client, admin_user):
        """Test admin can access user statistics"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/analytics/users", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "users_by_role" in data
        assert "most_active_users_top10" in data

    @pytest.mark.asyncio
    async def test_get_user_statistics_forbidden(self, client, manager_user):
        """Test manager cannot access user statistics"""
        from app.auth import create_access_token

        manager_token = create_access_token({"sub": manager_user.email})
        headers = {"Authorization": f"Bearer {manager_token}"}

        response = client.get("/api/v1/analytics/users", headers=headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_activity_statistics_admin(self, client, async_db_session, admin_user):
        """Test admin can access activity statistics"""
        from app.auth import create_access_token

        # Create test activity
        await log_activity(
            action="test_analytics",
            user_id=admin_user.id,
            description="Test",
        )

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/analytics/activity", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "total_activities" in data
        assert "activities_by_action" in data
        assert "daily_activities" in data
        assert "most_active_users_top10" in data

    @pytest.mark.asyncio
    async def test_get_activity_statistics_custom_period(self, client, admin_user):
        """Test activity statistics with custom period"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/analytics/activity?days=7", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7

    @pytest.mark.asyncio
    async def test_get_activity_statistics_max_period(self, client, admin_user):
        """Test activity statistics enforces max period"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Request more than max (365 days)
        response = client.get("/api/v1/analytics/activity?days=500", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 365  # Should be capped

    @pytest.mark.asyncio
    async def test_get_media_statistics_admin(self, client, async_db_session, admin_user):
        """Test admin can access media statistics"""
        from app.auth import create_access_token

        # Create test media
        media = Media(
            filename="stats_test.jpg",
            original_filename="stats_test.jpg",
            file_path="/tmp/stats_test.jpg",
            file_size=1024 * 500,
            mime_type="image/jpeg",
            file_type="image",
            uploaded_by=admin_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/analytics/media", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_media" in data
        assert "total_storage_bytes" in data
        assert "total_storage_mb" in data
        assert "media_by_type" in data
        assert "top_uploaders_top10" in data

    @pytest.mark.asyncio
    async def test_get_media_statistics_forbidden(self, client, manager_user):
        """Test manager cannot access media statistics"""
        from app.auth import create_access_token

        manager_token = create_access_token({"sub": manager_user.email})
        headers = {"Authorization": f"Bearer {manager_token}"}

        response = client.get("/api/v1/analytics/media", headers=headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user_performance_own(self, client, async_db_session, test_user):
        """Test user can view own performance report"""
        from app.auth import create_access_token

        # Create test content
        await create_test_content(
            async_db_session,
            title="Performance Test",
            body="Content",
            author_id=test_user.id,
        )

        token = create_access_token({"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/v1/analytics/user/{test_user.id}/performance", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["username"] == test_user.username
        assert "content_created" in data
        assert "total_activities" in data
        assert "media_uploaded" in data

    @pytest.mark.asyncio
    async def test_get_user_performance_other_forbidden(self, client, test_user, admin_user):
        """Test user cannot view other user's performance"""
        from app.auth import create_access_token

        token = create_access_token({"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/v1/analytics/user/{admin_user.id}/performance", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Not authorized" in data["error"]

    @pytest.mark.asyncio
    async def test_get_user_performance_admin_any_user(self, client, admin_user, test_user):
        """Test admin can view any user's performance"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get(f"/api/v1/analytics/user/{test_user.id}/performance", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id
        assert "content_created" in data

    @pytest.mark.asyncio
    async def test_get_my_performance(self, client, async_db_session, test_user):
        """Test user can view own performance via /my-performance"""
        from app.auth import create_access_token

        await create_test_content(
            async_db_session,
            title="My Performance Test",
            body="Content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        token = create_access_token({"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/analytics/my-performance", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["content_created"] >= 1
        assert "content_by_status" in data
        assert "published" in data["content_by_status"]

    @pytest.mark.asyncio
    async def test_get_my_performance_unauthorized(self, client):
        """Test my-performance requires authentication"""
        response = client.get("/api/v1/analytics/my-performance")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_performance_not_found(self, client, admin_user):
        """Test user performance handles non-existent user"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/analytics/user/99999/performance", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_analytics_endpoints_require_auth(self, client):
        """Test all analytics endpoints require authentication"""
        endpoints = [
            "/api/v1/analytics/dashboard",
            "/api/v1/analytics/content",
            "/api/v1/analytics/users",
            "/api/v1/analytics/activity",
            "/api/v1/analytics/media",
            "/api/v1/analytics/my-performance",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require auth"

    @pytest.mark.asyncio
    async def test_analytics_role_based_access(self, client, test_user, editor_user, manager_user, admin_user):
        """Test analytics endpoints have correct role requirements"""
        from app.auth import create_access_token

        # Dashboard: admin, superadmin, manager
        manager_token = create_access_token({"sub": manager_user.email})
        manager_headers = {"Authorization": f"Bearer {manager_token}"}
        response = client.get("/api/v1/analytics/dashboard", headers=manager_headers)
        assert response.status_code == 200

        # User stats: admin, superadmin only
        editor_token = create_access_token({"sub": editor_user.email})
        editor_headers = {"Authorization": f"Bearer {editor_token}"}
        response = client.get("/api/v1/analytics/users", headers=editor_headers)
        assert response.status_code == 403

        # Media stats: admin, superadmin only
        response = client.get("/api/v1/analytics/media", headers=manager_headers)
        assert response.status_code == 403
