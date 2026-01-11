"""
Tests for Export Service

Tests data export functionality in multiple formats (JSON, CSV).
"""

import csv
import json
from io import StringIO

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from utils.mock_utils import create_test_category, create_test_content, create_test_tag

from app.models.activity_log import ActivityLog
from app.models.content import ContentStatus
from app.models.user import User
from app.services.export_service import ExportService, export_service
from app.utils.activity_log import log_activity


class TestExportService:
    """Test export service functionality"""

    @pytest.fixture
    def export_svc(self):
        """Create export service instance"""
        return ExportService()

    @pytest.mark.asyncio
    async def test_export_content_json(self, async_db_session, test_user):
        """Test exporting content as JSON"""
        category = await create_test_category(async_db_session, name="Tech")
        tag = await create_test_tag(async_db_session, name="python")

        content = await create_test_content(
            async_db_session,
            title="Test Post",
            body="Test content",
            author_id=test_user.id,
            category_id=category.id,
            status=ContentStatus.PUBLISHED,
        )
        content.tags.append(tag)
        await async_db_session.commit()

        json_data = await export_service.export_content_json(db=async_db_session, limit=10)

        # Parse JSON
        data = json.loads(json_data)
        assert isinstance(data, list)
        assert len(data) >= 1

        # Verify structure
        exported_item = next((item for item in data if item["title"] == "Test Post"), None)
        assert exported_item is not None
        assert exported_item["title"] == "Test Post"
        assert exported_item["body"] == "Test content"
        assert exported_item["status"] == "published"
        assert exported_item["author"]["username"] == test_user.username
        assert exported_item["category"]["name"] == "Tech"
        assert len(exported_item["tags"]) == 1
        assert exported_item["tags"][0]["name"] == "python"

    @pytest.mark.asyncio
    async def test_export_content_json_with_filters(self, async_db_session, test_user):
        """Test exporting content with status filter"""
        draft = await create_test_content(
            async_db_session,
            title="Draft Post",
            body="Draft",
            author_id=test_user.id,
            status=ContentStatus.DRAFT,
        )
        published = await create_test_content(
            async_db_session,
            title="Published Post",
            body="Published",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        json_data = await export_service.export_content_json(db=async_db_session, status="published")

        data = json.loads(json_data)
        assert all(item["status"] == "published" for item in data)

    @pytest.mark.asyncio
    async def test_export_content_json_limit(self, async_db_session, test_user):
        """Test export respects limit parameter"""
        for i in range(10):
            await create_test_content(
                async_db_session,
                title=f"Post {i}",
                body="Content",
                author_id=test_user.id,
            )

        json_data = await export_service.export_content_json(db=async_db_session, limit=5)

        data = json.loads(json_data)
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_export_content_csv(self, async_db_session, test_user):
        """Test exporting content as CSV"""
        category = await create_test_category(async_db_session, name="News")
        tag1 = await create_test_tag(async_db_session, name="breaking")
        tag2 = await create_test_tag(async_db_session, name="important")

        content = await create_test_content(
            async_db_session,
            title="News Article",
            body="News content",
            author_id=test_user.id,
            category_id=category.id,
        )
        content.tags.extend([tag1, tag2])
        await async_db_session.commit()

        csv_data = await export_service.export_content_csv(db=async_db_session)

        # Parse CSV
        csv_file = StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        rows = list(reader)

        assert len(rows) >= 1

        # Find our content
        exported_row = next((row for row in rows if row["Title"] == "News Article"), None)
        assert exported_row is not None
        assert exported_row["Title"] == "News Article"
        assert exported_row["Status"] == "draft"
        assert exported_row["Author Username"] == test_user.username
        assert exported_row["Category"] == "News"
        assert "breaking" in exported_row["Tags"]
        assert "important" in exported_row["Tags"]

    @pytest.mark.asyncio
    async def test_export_content_csv_headers(self, async_db_session):
        """Test CSV export has correct headers"""
        csv_data = await export_service.export_content_csv(db=async_db_session)

        csv_file = StringIO(csv_data)
        reader = csv.reader(csv_file)
        headers = next(reader)

        expected_headers = [
            "ID",
            "Title",
            "Slug",
            "Status",
            "Author Username",
            "Author Email",
            "Category",
            "Tags",
            "Created At",
            "Updated At",
            "Publish At",
        ]
        assert headers == expected_headers

    @pytest.mark.asyncio
    async def test_export_users_json(self, async_db_session, test_user):
        """Test exporting users as JSON"""
        json_data = await export_service.export_users_json(db=async_db_session)

        data = json.loads(json_data)
        assert isinstance(data, list)
        assert len(data) >= 1

        # Find test user
        exported_user = next((user for user in data if user["username"] == test_user.username), None)
        assert exported_user is not None
        assert exported_user["email"] == test_user.email
        assert "role" in exported_user
        assert exported_user["role"]["name"] == test_user.role.name

    @pytest.mark.asyncio
    async def test_export_users_json_with_role_filter(self, async_db_session, admin_user, test_user):
        """Test exporting users filtered by role"""
        json_data = await export_service.export_users_json(db=async_db_session, role_id=admin_user.role_id)

        data = json.loads(json_data)
        assert all(user["role"]["id"] == admin_user.role_id for user in data)

    @pytest.mark.asyncio
    async def test_export_users_csv(self, async_db_session, test_user):
        """Test exporting users as CSV"""
        csv_data = await export_service.export_users_csv(db=async_db_session)

        csv_file = StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        rows = list(reader)

        assert len(rows) >= 1

        # Find test user
        exported_user = next((row for row in rows if row["Username"] == test_user.username), None)
        assert exported_user is not None
        assert exported_user["Email"] == test_user.email
        assert exported_user["Role"] == test_user.role.name

    @pytest.mark.asyncio
    async def test_export_users_csv_headers(self, async_db_session):
        """Test users CSV has correct headers"""
        csv_data = await export_service.export_users_csv(db=async_db_session)

        csv_file = StringIO(csv_data)
        reader = csv.reader(csv_file)
        headers = next(reader)

        assert headers == ["ID", "Username", "Email", "Role"]

    @pytest.mark.asyncio
    async def test_export_activity_logs_json(self, async_db_session, test_user):
        """Test exporting activity logs as JSON"""
        # Create test activity logs
        await log_activity(
            action="test_action",
            user_id=test_user.id,
            description="Test activity",
        )

        json_data = await export_service.export_activity_logs_json(db=async_db_session, limit=100)

        data = json.loads(json_data)
        assert isinstance(data, list)
        assert len(data) >= 1

        # Verify structure
        log_item = data[0]
        assert "id" in log_item
        assert "action" in log_item
        assert "description" in log_item
        assert "timestamp" in log_item

    @pytest.mark.asyncio
    async def test_export_activity_logs_json_with_filters(self, async_db_session, test_user):
        """Test exporting activity logs with filters"""
        await log_activity(
            action="content_created",
            user_id=test_user.id,
            description="Created content",
        )
        await log_activity(
            action="user_logged_in",
            user_id=test_user.id,
            description="User logged in",
        )

        # Filter by action
        json_data = await export_service.export_activity_logs_json(
            db=async_db_session, action="content_created", limit=100
        )

        data = json.loads(json_data)
        assert all(log["action"] == "content_created" for log in data)

        # Filter by user
        json_data = await export_service.export_activity_logs_json(db=async_db_session, user_id=test_user.id, limit=100)

        data = json.loads(json_data)
        assert all(log["user"]["id"] == test_user.id for log in data if log["user"])

    @pytest.mark.asyncio
    async def test_export_activity_logs_csv(self, async_db_session, test_user):
        """Test exporting activity logs as CSV"""
        await log_activity(
            action="test_export",
            user_id=test_user.id,
            description="Test CSV export",
        )

        csv_data = await export_service.export_activity_logs_csv(db=async_db_session)

        csv_file = StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        rows = list(reader)

        assert len(rows) >= 1

        # Find our log
        exported_log = next((row for row in rows if row["Action"] == "test_export"), None)
        assert exported_log is not None
        assert exported_log["Description"] == "Test CSV export"
        assert exported_log["Username"] == test_user.username

    @pytest.mark.asyncio
    async def test_export_activity_logs_csv_headers(self, async_db_session):
        """Test activity logs CSV has correct headers"""
        csv_data = await export_service.export_activity_logs_csv(db=async_db_session)

        csv_file = StringIO(csv_data)
        reader = csv.reader(csv_file)
        headers = next(reader)

        expected_headers = [
            "ID",
            "Action",
            "Description",
            "User ID",
            "Username",
            "Content ID",
            "Target User ID",
            "Timestamp",
        ]
        assert headers == expected_headers

    @pytest.mark.asyncio
    async def test_export_activity_logs_limit(self, async_db_session, test_user):
        """Test activity logs export respects limit"""
        # Create multiple logs
        for i in range(20):
            await log_activity(
                action=f"action_{i}",
                user_id=test_user.id,
                description=f"Activity {i}",
            )

        json_data = await export_service.export_activity_logs_json(db=async_db_session, limit=10)

        data = json.loads(json_data)
        assert len(data) == 10

    @pytest.mark.asyncio
    async def test_export_empty_results(self, async_db_session):
        """Test exports handle empty results gracefully"""
        json_data = await export_service.export_content_json(db=async_db_session, status="nonexistent")
        data = json.loads(json_data)
        assert data == []

        csv_data = await export_service.export_content_csv(db=async_db_session, author_id=99999)
        csv_file = StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        assert len(rows) == 0

    async def test_singleton_instance(self):
        """Test export_service singleton exists"""
        assert export_service is not None
        assert isinstance(export_service, ExportService)
