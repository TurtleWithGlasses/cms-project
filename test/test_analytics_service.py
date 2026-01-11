"""
Tests for Analytics Service

Tests analytics and reporting for content, users, and system activity.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from utils.mock_utils import create_test_category, create_test_content

from app.models.content import ContentStatus
from app.models.media import Media
from app.services.analytics_service import AnalyticsService, analytics_service
from app.utils.activity_log import log_activity


class TestAnalyticsService:
    """Test analytics service functionality"""

    @pytest.fixture
    def analytics_svc(self):
        """Create analytics service instance"""
        return AnalyticsService()

    @pytest.mark.asyncio
    async def test_get_content_statistics(self, async_db_session, test_user):
        """Test getting content statistics"""
        # Create content with different statuses
        await create_test_content(
            async_db_session,
            title="Draft Post",
            body="Content",
            author_id=test_user.id,
            status=ContentStatus.DRAFT,
        )
        await create_test_content(
            async_db_session,
            title="Published Post",
            body="Content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        stats = await analytics_service.get_content_statistics(async_db_session)

        assert "total_content" in stats
        assert "content_by_status" in stats
        assert "recent_content_30_days" in stats
        assert "content_by_category_top10" in stats

        assert stats["total_content"] >= 2
        assert "draft" in stats["content_by_status"]
        assert "published" in stats["content_by_status"]

    @pytest.mark.asyncio
    async def test_get_content_statistics_by_category(self, async_db_session, test_user):
        """Test content statistics include category breakdown"""
        category1 = await create_test_category(async_db_session, name="Tech")
        category2 = await create_test_category(async_db_session, name="News")

        # Create content in different categories
        for i in range(3):
            await create_test_content(
                async_db_session,
                title=f"Tech Post {i}",
                body="Content",
                author_id=test_user.id,
                category_id=category1.id,
            )

        await create_test_content(
            async_db_session,
            title="News Post",
            body="Content",
            author_id=test_user.id,
            category_id=category2.id,
        )

        stats = await analytics_service.get_content_statistics(async_db_session)

        assert len(stats["content_by_category_top10"]) >= 2
        # Tech category should have more content
        tech_count = next(
            (cat["count"] for cat in stats["content_by_category_top10"] if cat["category_id"] == category1.id),
            0,
        )
        assert tech_count >= 3

    @pytest.mark.asyncio
    async def test_get_user_statistics(self, async_db_session, test_user):
        """Test getting user statistics"""
        # Create content for test user
        await create_test_content(
            async_db_session,
            title="User Post",
            body="Content",
            author_id=test_user.id,
        )

        stats = await analytics_service.get_user_statistics(async_db_session)

        assert "total_users" in stats
        assert "users_by_role" in stats
        assert "most_active_users_top10" in stats

        assert stats["total_users"] >= 1
        assert len(stats["users_by_role"]) >= 1

        # Test user should be in most active users
        active_user_ids = [user["user_id"] for user in stats["most_active_users_top10"]]
        assert test_user.id in active_user_ids

    @pytest.mark.asyncio
    async def test_get_user_statistics_most_active(self, async_db_session, test_user, admin_user):
        """Test most active users are correctly identified"""
        # Create multiple content for test_user
        for i in range(5):
            await create_test_content(
                async_db_session,
                title=f"Post {i}",
                body="Content",
                author_id=test_user.id,
            )

        # Create less content for admin
        await create_test_content(
            async_db_session,
            title="Admin Post",
            body="Content",
            author_id=admin_user.id,
        )

        stats = await analytics_service.get_user_statistics(async_db_session)

        # test_user should have higher content count
        test_user_stats = next(
            (user for user in stats["most_active_users_top10"] if user["user_id"] == test_user.id),
            None,
        )
        assert test_user_stats is not None
        assert test_user_stats["content_count"] >= 5

    @pytest.mark.asyncio
    async def test_get_activity_statistics(self, async_db_session, test_user):
        """Test getting activity statistics"""
        # Create test activities
        for i in range(5):
            await log_activity(
                action=f"test_action_{i}",
                user_id=test_user.id,
                description=f"Test activity {i}",
            )

        stats = await analytics_service.get_activity_statistics(async_db_session, days=30)

        assert "period_days" in stats
        assert "total_activities" in stats
        assert "activities_by_action" in stats
        assert "daily_activities" in stats
        assert "most_active_users_top10" in stats

        assert stats["period_days"] == 30
        assert stats["total_activities"] >= 5

    @pytest.mark.asyncio
    async def test_get_activity_statistics_by_action(self, async_db_session, test_user):
        """Test activity statistics breakdown by action"""
        # Create activities with different actions
        for _ in range(3):
            await log_activity(
                action="content_created",
                user_id=test_user.id,
                description="Created content",
            )

        for _ in range(2):
            await log_activity(
                action="user_logged_in",
                user_id=test_user.id,
                description="Logged in",
            )

        stats = await analytics_service.get_activity_statistics(async_db_session, days=30)

        assert "content_created" in stats["activities_by_action"]
        assert "user_logged_in" in stats["activities_by_action"]
        assert stats["activities_by_action"]["content_created"] >= 3
        assert stats["activities_by_action"]["user_logged_in"] >= 2

    @pytest.mark.asyncio
    async def test_get_activity_statistics_custom_period(self, async_db_session, test_user):
        """Test activity statistics for custom time period"""
        # Create old activity
        await log_activity(
            action="old_action",
            user_id=test_user.id,
            description="Old activity",
        )

        stats_7_days = await analytics_service.get_activity_statistics(async_db_session, days=7)
        stats_30_days = await analytics_service.get_activity_statistics(async_db_session, days=30)

        assert stats_7_days["period_days"] == 7
        assert stats_30_days["period_days"] == 30
        # 30 days should have more or equal activities
        assert stats_30_days["total_activities"] >= stats_7_days["total_activities"]

    @pytest.mark.asyncio
    async def test_get_media_statistics(self, async_db_session, test_user):
        """Test getting media statistics"""
        # Create test media
        media1 = Media(
            filename="test1.jpg",
            original_filename="test1.jpg",
            file_path="/tmp/test1.jpg",
            file_size=1024 * 500,  # 500KB
            mime_type="image/jpeg",
            file_type="image",
            uploaded_by=test_user.id,
        )
        media2 = Media(
            filename="test2.pdf",
            original_filename="test2.pdf",
            file_path="/tmp/test2.pdf",
            file_size=1024 * 1024 * 2,  # 2MB
            mime_type="application/pdf",
            file_type="document",
            uploaded_by=test_user.id,
        )
        async_db_session.add(media1)
        async_db_session.add(media2)
        await async_db_session.commit()

        stats = await analytics_service.get_media_statistics(async_db_session)

        assert "total_media" in stats
        assert "total_storage_bytes" in stats
        assert "total_storage_mb" in stats
        assert "media_by_type" in stats
        assert "top_uploaders_top10" in stats

        assert stats["total_media"] >= 2
        assert stats["total_storage_bytes"] >= (1024 * 500 + 1024 * 1024 * 2)
        assert "image" in stats["media_by_type"]
        assert "document" in stats["media_by_type"]

    @pytest.mark.asyncio
    async def test_get_media_statistics_top_uploaders(self, async_db_session, test_user, admin_user):
        """Test media statistics identify top uploaders"""
        # Upload multiple files as test_user
        for i in range(5):
            media = Media(
                filename=f"file{i}.jpg",
                original_filename=f"file{i}.jpg",
                file_path=f"/tmp/file{i}.jpg",
                file_size=1024 * 100,
                mime_type="image/jpeg",
                file_type="image",
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)

        # Upload less as admin
        media = Media(
            filename="admin.jpg",
            original_filename="admin.jpg",
            file_path="/tmp/admin.jpg",
            file_size=1024 * 100,
            mime_type="image/jpeg",
            file_type="image",
            uploaded_by=admin_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()

        stats = await analytics_service.get_media_statistics(async_db_session)

        # test_user should be top uploader
        test_user_stats = next(
            (user for user in stats["top_uploaders_top10"] if user["user_id"] == test_user.id),
            None,
        )
        assert test_user_stats is not None
        assert test_user_stats["upload_count"] >= 5

    @pytest.mark.asyncio
    async def test_get_dashboard_overview(self, async_db_session, test_user):
        """Test getting complete dashboard overview"""
        # Create test data
        await create_test_content(
            async_db_session,
            title="Dashboard Test",
            body="Content",
            author_id=test_user.id,
        )
        await log_activity(
            action="dashboard_test",
            user_id=test_user.id,
            description="Test",
        )

        overview = await analytics_service.get_dashboard_overview(async_db_session)

        assert "content" in overview
        assert "users" in overview
        assert "activity" in overview
        assert "media" in overview
        assert "generated_at" in overview

        # Verify each section has expected data
        assert "total_content" in overview["content"]
        assert "total_users" in overview["users"]
        assert "total_activities" in overview["activity"]
        assert "total_media" in overview["media"]

    @pytest.mark.asyncio
    async def test_get_user_performance_report(self, async_db_session, test_user):
        """Test getting user performance report"""
        # Create test data for user
        for i in range(3):
            await create_test_content(
                async_db_session,
                title=f"User Post {i}",
                body="Content",
                author_id=test_user.id,
                status=ContentStatus.PUBLISHED,
            )

        await log_activity(
            action="test_performance",
            user_id=test_user.id,
            description="Performance test",
        )

        media = Media(
            filename="user_media.jpg",
            original_filename="user_media.jpg",
            file_path="/tmp/user_media.jpg",
            file_size=1024 * 500,
            mime_type="image/jpeg",
            file_type="image",
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()

        report = await analytics_service.get_user_performance_report(async_db_session, test_user.id)

        assert report["user_id"] == test_user.id
        assert report["username"] == test_user.username
        assert report["email"] == test_user.email
        assert report["role"] == test_user.role.name
        assert report["content_created"] >= 3
        assert "published" in report["content_by_status"]
        assert report["total_activities"] >= 1
        assert report["media_uploaded"] >= 1
        assert report["storage_used_bytes"] >= (1024 * 500)

    @pytest.mark.asyncio
    async def test_get_user_performance_report_not_found(self, async_db_session):
        """Test user performance report handles non-existent user"""
        report = await analytics_service.get_user_performance_report(async_db_session, 99999)

        assert "error" in report
        assert "not found" in report["error"].lower()

    @pytest.mark.asyncio
    async def test_get_user_performance_report_no_activity(self, async_db_session):
        """Test user performance report handles user with no activity"""
        from app.models.user import Role, User

        # Create user with no activity
        role_result = await async_db_session.execute(__import__("sqlalchemy").select(Role).where(Role.name == "user"))
        role = role_result.scalars().first()

        inactive_user = User(
            email="inactive@example.com",
            username="inactiveuser",
            hashed_password="hashed",
            role_id=role.id,
        )
        async_db_session.add(inactive_user)
        await async_db_session.commit()
        await async_db_session.refresh(inactive_user)

        report = await analytics_service.get_user_performance_report(async_db_session, inactive_user.id)

        assert report["user_id"] == inactive_user.id
        assert report["content_created"] == 0
        assert report["total_activities"] == 0
        assert report["media_uploaded"] == 0

    async def test_singleton_instance(self):
        """Test analytics_service singleton exists"""
        assert analytics_service is not None
        assert isinstance(analytics_service, AnalyticsService)
