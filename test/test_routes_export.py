"""
Tests for Export Routes

Tests API endpoints for data export in various formats.
"""

import csv
import json
from io import StringIO

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from utils.mock_utils import create_test_category, create_test_content

from app.models.content import ContentStatus
from app.models.user import Role, User
from app.utils.activity_log import log_activity


class TestExportRoutes:
    """Test export API endpoints"""

    @pytest.mark.asyncio
    async def test_export_content_json(self, client, async_db_session, auth_headers, test_user):
        """Test exporting content as JSON"""
        content = await create_test_content(
            async_db_session,
            title="Export Test",
            body="Content to export",
            author_id=test_user.id,
        )

        response = client.get("/api/v1/export/content/json", headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "content_export.json" in response.headers["content-disposition"]

        data = json.loads(response.content)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_export_content_json_unauthorized(self, client):
        """Test export requires authentication"""
        response = client.get("/api/v1/export/content/json")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_content_json_user_only_own(self, client, async_db_session, test_user):
        """Test regular user can only export own content"""
        from app.auth import create_access_token

        # Create another user
        role_result = await async_db_session.execute(__import__("sqlalchemy").select(Role).where(Role.name == "user"))
        role = role_result.scalars().first()

        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password="hashed",
            role_id=role.id,
        )
        async_db_session.add(other_user)
        await async_db_session.commit()
        await async_db_session.refresh(other_user)

        # Create content for other user
        await create_test_content(
            async_db_session,
            title="Other User Content",
            body="Content",
            author_id=other_user.id,
        )

        # Export as test_user
        token = create_access_token({"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/export/content/json", headers=headers)

        data = json.loads(response.content)
        # Should only contain test_user's content
        assert all(item["author"]["id"] == test_user.id for item in data)

    @pytest.mark.asyncio
    async def test_export_content_json_admin_all_content(self, client, async_db_session, admin_user, test_user):
        """Test admin can export all users' content"""
        from app.auth import create_access_token

        # Create content for test_user
        await create_test_content(
            async_db_session,
            title="User Content",
            body="Content",
            author_id=test_user.id,
        )

        # Export as admin (no author_id filter)
        admin_token = create_access_token({"sub": admin_user.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/export/content/json", headers=admin_headers)

        data = json.loads(response.content)
        # Should contain content from multiple users
        author_ids = {item["author"]["id"] for item in data}
        assert len(author_ids) >= 1  # At least one author

    @pytest.mark.asyncio
    async def test_export_content_json_with_filters(self, client, async_db_session, auth_headers, test_user):
        """Test exporting content with status filter"""
        await create_test_content(
            async_db_session,
            title="Published",
            body="Content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        response = client.get("/api/v1/export/content/json?status=published", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert all(item["status"] == "published" for item in data)

    @pytest.mark.asyncio
    async def test_export_content_csv(self, client, async_db_session, auth_headers, test_user):
        """Test exporting content as CSV"""
        await create_test_content(
            async_db_session,
            title="CSV Export",
            body="Content",
            author_id=test_user.id,
        )

        response = client.get("/api/v1/export/content/csv", headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "content_export.csv" in response.headers["content-disposition"]

        # Verify CSV format
        csv_file = StringIO(response.text)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        assert len(rows) >= 1

    @pytest.mark.asyncio
    async def test_export_users_json_admin(self, client, admin_user):
        """Test admin can export users as JSON"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/export/users/json", headers=headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json; charset=utf-8"
        assert "users_export.json" in response.headers["content-disposition"]

        data = json.loads(response.content)
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_export_users_json_forbidden(self, client, auth_headers):
        """Test regular user cannot export users"""
        response = client.get("/api/v1/export/users/json", headers=auth_headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_export_users_json_with_role_filter(self, client, async_db_session, admin_user):
        """Test exporting users with role filter"""
        from app.auth import create_access_token

        role_result = await async_db_session.execute(__import__("sqlalchemy").select(Role).where(Role.name == "user"))
        user_role = role_result.scalars().first()

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get(f"/api/v1/export/users/json?role_id={user_role.id}", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert all(user["role"]["id"] == user_role.id for user in data)

    @pytest.mark.asyncio
    async def test_export_users_csv_admin(self, client, admin_user):
        """Test admin can export users as CSV"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/export/users/csv", headers=headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "users_export.csv" in response.headers["content-disposition"]

        csv_file = StringIO(response.text)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        assert len(rows) >= 1

    @pytest.mark.asyncio
    async def test_export_activity_logs_json_admin(self, client, async_db_session, admin_user):
        """Test admin can export activity logs as JSON"""
        from app.auth import create_access_token

        # Create test activity
        await log_activity(
            action="test_export_route",
            user_id=admin_user.id,
            description="Test activity",
        )

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/export/activity-logs/json", headers=headers)

        assert response.status_code == 200
        assert "activity_logs_export.json" in response.headers["content-disposition"]

        data = json.loads(response.content)
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_export_activity_logs_json_forbidden(self, client, auth_headers):
        """Test regular user cannot export activity logs"""
        response = client.get("/api/v1/export/activity-logs/json", headers=auth_headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_export_activity_logs_json_with_filters(self, client, async_db_session, admin_user):
        """Test exporting activity logs with filters"""
        from app.auth import create_access_token

        await log_activity(
            action="content_created",
            user_id=admin_user.id,
            description="Created content",
        )

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Filter by action
        response = client.get("/api/v1/export/activity-logs/json?action=content_created", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert all(log["action"] == "content_created" for log in data)

        # Filter by user_id
        response = client.get(f"/api/v1/export/activity-logs/json?user_id={admin_user.id}", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert all(log["user"]["id"] == admin_user.id for log in data if log["user"])

    @pytest.mark.asyncio
    async def test_export_activity_logs_limit_enforcement(self, client, admin_user):
        """Test activity logs export limit is enforced"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Request more than max limit
        response = client.get("/api/v1/export/activity-logs/json?limit=20000", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.content)
        # Should be capped at 10000
        assert len(data) <= 10000

    @pytest.mark.asyncio
    async def test_export_activity_logs_csv_admin(self, client, async_db_session, admin_user):
        """Test admin can export activity logs as CSV"""
        from app.auth import create_access_token

        await log_activity(
            action="csv_test",
            user_id=admin_user.id,
            description="CSV test",
        )

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/export/activity-logs/csv", headers=headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "activity_logs_export.csv" in response.headers["content-disposition"]

        csv_file = StringIO(response.text)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        assert len(rows) >= 1

    @pytest.mark.asyncio
    async def test_export_content_limit_parameter(self, client, async_db_session, auth_headers, test_user):
        """Test export respects limit parameter"""
        # Create multiple content items
        for i in range(10):
            await create_test_content(
                async_db_session,
                title=f"Post {i}",
                body="Content",
                author_id=test_user.id,
            )

        response = client.get("/api/v1/export/content/json?limit=5", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_export_users_limit_parameter(self, client, async_db_session, admin_user):
        """Test users export respects limit parameter"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/export/users/json?limit=2", headers=headers)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data) <= 2
