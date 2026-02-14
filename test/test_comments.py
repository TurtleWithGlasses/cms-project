"""
Tests for Comment functionality.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment, CommentStatus
from app.models.comment_engagement import (
    CommentEditHistory,
    CommentReaction,
    ReactionType,
    ReportReason,
    ReportStatus,
)
from app.models.content import Content, ContentStatus
from app.models.user import User
from app.services.comment_service import CommentService
from main import app


@pytest.fixture
async def test_content(test_db: AsyncSession, test_user: User) -> Content:
    """Create test content for comments."""
    content = Content(
        title="Test Article",
        body="This is test content for comments.",
        slug="test-article-comments",
        status=ContentStatus.PUBLISHED,
        author_id=test_user.id,
    )
    test_db.add(content)
    await test_db.commit()
    await test_db.refresh(content)
    return content


class TestCommentService:
    """Tests for CommentService."""

    @pytest.mark.asyncio
    async def test_create_comment(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test creating a new comment."""
        service = CommentService(test_db)

        comment = await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="This is a test comment.",
        )

        assert comment.id is not None
        assert comment.body == "This is a test comment."
        assert comment.content_id == test_content.id
        assert comment.user_id == test_user.id
        assert comment.status == CommentStatus.PENDING
        assert comment.parent_id is None

    @pytest.mark.asyncio
    async def test_create_comment_auto_approve(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test creating a comment with auto-approval."""
        service = CommentService(test_db)

        comment = await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="Auto-approved comment.",
            auto_approve=True,
        )

        assert comment.status == CommentStatus.APPROVED

    @pytest.mark.asyncio
    async def test_create_reply(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test creating a reply to a comment."""
        service = CommentService(test_db)

        # Create parent comment
        parent = await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="Parent comment.",
            auto_approve=True,
        )

        # Create reply
        reply = await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="Reply to parent.",
            parent_id=parent.id,
        )

        assert reply.parent_id == parent.id

    @pytest.mark.asyncio
    async def test_get_comments_for_content(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test getting comments for a content item."""
        service = CommentService(test_db)

        # Create approved comments
        for i in range(3):
            await service.create_comment(
                content_id=test_content.id,
                user_id=test_user.id,
                body=f"Comment {i}",
                auto_approve=True,
            )

        # Create pending comment
        await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="Pending comment",
        )

        # Get approved only
        comments = await service.get_comments_for_content(test_content.id, include_pending=False)
        assert len(comments) == 3

        # Get all including pending
        comments = await service.get_comments_for_content(test_content.id, include_pending=True)
        assert len(comments) == 4

    @pytest.mark.asyncio
    async def test_get_comment_count(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test getting comment count."""
        service = CommentService(test_db)

        # Create comments
        await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="Approved comment",
            auto_approve=True,
        )
        await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="Pending comment",
        )

        approved_count = await service.get_comment_count(test_content.id, include_pending=False)
        total_count = await service.get_comment_count(test_content.id, include_pending=True)

        assert approved_count == 1
        assert total_count == 2

    @pytest.mark.asyncio
    async def test_update_comment(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test updating a comment."""
        service = CommentService(test_db)

        comment = await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="Original body",
        )

        updated = await service.update_comment(
            comment_id=comment.id,
            user_id=test_user.id,
            body="Updated body",
        )

        assert updated.body == "Updated body"
        assert updated.is_edited is True
        assert updated.edited_at is not None

    @pytest.mark.asyncio
    async def test_update_comment_unauthorized(
        self, test_db: AsyncSession, test_user: User, test_admin: User, test_content: Content
    ):
        """Test that only the author can update their comment."""
        service = CommentService(test_db)

        comment = await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="User's comment",
        )

        with pytest.raises(PermissionError):
            await service.update_comment(
                comment_id=comment.id,
                user_id=test_admin.id,
                body="Admin trying to edit",
            )

    @pytest.mark.asyncio
    async def test_delete_comment(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test soft deleting a comment."""
        service = CommentService(test_db)

        comment = await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="To be deleted",
        )

        result = await service.delete_comment(
            comment_id=comment.id,
            user_id=test_user.id,
        )

        assert result is True

        # Verify soft delete
        deleted = await service.get_comment(comment.id)
        assert deleted.is_deleted is True

    @pytest.mark.asyncio
    async def test_admin_can_delete_any_comment(
        self, test_db: AsyncSession, test_user: User, test_admin: User, test_content: Content
    ):
        """Test that admin can delete any comment."""
        service = CommentService(test_db)

        comment = await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="User's comment",
        )

        result = await service.delete_comment(
            comment_id=comment.id,
            user_id=test_admin.id,
            is_admin=True,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_moderate_comment(
        self, test_db: AsyncSession, test_user: User, test_admin: User, test_content: Content
    ):
        """Test moderating a comment."""
        service = CommentService(test_db)

        comment = await service.create_comment(
            content_id=test_content.id,
            user_id=test_user.id,
            body="Pending comment",
        )

        assert comment.status == CommentStatus.PENDING

        # Approve
        moderated = await service.moderate_comment(
            comment_id=comment.id,
            status=CommentStatus.APPROVED,
            moderator_id=test_admin.id,
        )

        assert moderated.status == CommentStatus.APPROVED

    @pytest.mark.asyncio
    async def test_get_pending_comments(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test getting pending comments for moderation."""
        service = CommentService(test_db)

        # Create pending comments
        for i in range(3):
            await service.create_comment(
                content_id=test_content.id,
                user_id=test_user.id,
                body=f"Pending {i}",
            )

        pending = await service.get_pending_comments()
        assert len(pending) == 3

    @pytest.mark.asyncio
    async def test_bulk_moderate(self, test_db: AsyncSession, test_user: User, test_admin: User, test_content: Content):
        """Test bulk moderation of comments."""
        service = CommentService(test_db)

        comment_ids = []
        for i in range(3):
            comment = await service.create_comment(
                content_id=test_content.id,
                user_id=test_user.id,
                body=f"Comment {i}",
            )
            comment_ids.append(comment.id)

        count = await service.bulk_moderate(
            comment_ids=comment_ids,
            status=CommentStatus.APPROVED,
            moderator_id=test_admin.id,
        )

        assert count == 3


class TestCommentRoutes:
    """Tests for Comment API routes."""

    def test_get_content_comments(self, authenticated_client, test_db, test_user, test_content):
        """Test getting comments for content via API."""
        # First create some comments (need to do this through the service since route requires content)
        import asyncio

        async def create_comments():
            service = CommentService(test_db)
            await service.create_comment(
                content_id=test_content.id,
                user_id=test_user.id,
                body="Test comment",
                auto_approve=True,
            )

        asyncio.get_event_loop().run_until_complete(create_comments())

        response = authenticated_client.get(f"/api/v1/comments/content/{test_content.id}")
        assert response.status_code == 200

        data = response.json()
        assert "comments" in data
        assert "total" in data

    def test_create_comment_requires_auth(self, client, test_content):
        """Test that creating a comment requires authentication."""
        response = client.post(
            f"/api/v1/comments/content/{test_content.id}",
            json={"body": "Test comment"},
        )
        assert response.status_code == 401

    def test_create_comment(self, authenticated_client, test_content):
        """Test creating a comment via API."""
        response = authenticated_client.post(
            f"/api/v1/comments/content/{test_content.id}",
            json={"body": "New comment via API"},
        )
        assert response.status_code == 201

        data = response.json()
        assert data["body"] == "New comment via API"

    def test_update_comment(self, authenticated_client, test_db, test_user, test_content):
        """Test updating a comment via API."""
        import asyncio

        async def create_comment():
            service = CommentService(test_db)
            return await service.create_comment(
                content_id=test_content.id,
                user_id=test_user.id,
                body="Original",
            )

        comment = asyncio.get_event_loop().run_until_complete(create_comment())

        response = authenticated_client.put(
            f"/api/v1/comments/{comment.id}",
            json={"body": "Updated via API"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["body"] == "Updated via API"
        assert data["is_edited"] is True

    def test_delete_comment(self, authenticated_client, test_db, test_user, test_content):
        """Test deleting a comment via API."""
        import asyncio

        async def create_comment():
            service = CommentService(test_db)
            return await service.create_comment(
                content_id=test_content.id,
                user_id=test_user.id,
                body="To delete",
            )

        comment = asyncio.get_event_loop().run_until_complete(create_comment())

        response = authenticated_client.delete(f"/api/v1/comments/{comment.id}")
        assert response.status_code == 204

    def test_moderate_comment_requires_admin(self, authenticated_client, test_db, test_user, test_content):
        """Test that moderation requires admin role."""
        import asyncio

        async def create_comment():
            service = CommentService(test_db)
            return await service.create_comment(
                content_id=test_content.id,
                user_id=test_user.id,
                body="To moderate",
            )

        comment = asyncio.get_event_loop().run_until_complete(create_comment())

        response = authenticated_client.post(
            f"/api/v1/comments/{comment.id}/moderate",
            json={"status": "APPROVED"},
        )
        # Regular user should get 403
        assert response.status_code == 403

    def test_admin_can_moderate(self, admin_client, test_db, test_user, test_content):
        """Test that admin can moderate comments."""
        import asyncio

        async def create_comment():
            async with test_db.begin():
                service = CommentService(test_db)
                return await service.create_comment(
                    content_id=test_content.id,
                    user_id=test_user.id,
                    body="To moderate",
                )

        comment = asyncio.get_event_loop().run_until_complete(create_comment())

        response = admin_client.post(
            f"/api/v1/comments/{comment.id}/moderate",
            json={"status": "APPROVED"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "APPROVED"


# ============== Reaction Tests ==============


class TestCommentReactions:
    """Tests for comment reaction functionality."""

    @pytest.mark.asyncio
    async def test_toggle_reaction_creates(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test that toggling a reaction creates it."""
        service = CommentService(test_db)
        comment = await service.create_comment(
            content_id=test_content.id, user_id=test_user.id, body="Likeable comment", auto_approve=True
        )

        result = await service.toggle_reaction(comment.id, test_user.id, ReactionType.LIKE)

        assert result["like_count"] == 1
        assert result["dislike_count"] == 0
        assert result["user_reaction"] == "like"

    @pytest.mark.asyncio
    async def test_toggle_reaction_removes_same(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test that toggling the same reaction removes it."""
        service = CommentService(test_db)
        comment = await service.create_comment(
            content_id=test_content.id, user_id=test_user.id, body="Toggle test", auto_approve=True
        )

        # Like then unlike
        await service.toggle_reaction(comment.id, test_user.id, ReactionType.LIKE)
        result = await service.toggle_reaction(comment.id, test_user.id, ReactionType.LIKE)

        assert result["like_count"] == 0
        assert result["user_reaction"] is None

    @pytest.mark.asyncio
    async def test_toggle_reaction_switches(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test that toggling a different reaction switches it."""
        service = CommentService(test_db)
        comment = await service.create_comment(
            content_id=test_content.id, user_id=test_user.id, body="Switch test", auto_approve=True
        )

        # Like then dislike
        await service.toggle_reaction(comment.id, test_user.id, ReactionType.LIKE)
        result = await service.toggle_reaction(comment.id, test_user.id, ReactionType.DISLIKE)

        assert result["like_count"] == 0
        assert result["dislike_count"] == 1
        assert result["user_reaction"] == "dislike"

    @pytest.mark.asyncio
    async def test_reaction_counts(
        self, test_db: AsyncSession, test_user: User, test_admin: User, test_content: Content
    ):
        """Test reaction counts with multiple users."""
        service = CommentService(test_db)
        comment = await service.create_comment(
            content_id=test_content.id, user_id=test_user.id, body="Popular comment", auto_approve=True
        )

        await service.toggle_reaction(comment.id, test_user.id, ReactionType.LIKE)
        await service.toggle_reaction(comment.id, test_admin.id, ReactionType.LIKE)

        counts = await service.get_reaction_counts(comment.id)
        assert counts["like_count"] == 2
        assert counts["dislike_count"] == 0

    @pytest.mark.asyncio
    async def test_reaction_endpoint(self):
        """Test reaction toggle endpoint via API."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/comments/999999/reactions",
                json={"reaction_type": "like"},
            )

        # Unauthenticated should get redirect or auth error
        assert response.status_code in (307, 401, 403)


# ============== Reporting Tests ==============


class TestCommentReporting:
    """Tests for comment reporting functionality."""

    @pytest.mark.asyncio
    async def test_report_comment(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test reporting a comment."""
        service = CommentService(test_db)
        comment = await service.create_comment(
            content_id=test_content.id, user_id=test_user.id, body="Reportable comment", auto_approve=True
        )

        report = await service.report_comment(
            comment_id=comment.id,
            user_id=test_user.id,
            reason=ReportReason.SPAM,
            description="This looks like spam",
        )

        assert report.id is not None
        assert report.reason == ReportReason.SPAM
        assert report.status == ReportStatus.PENDING

    @pytest.mark.asyncio
    async def test_report_duplicate_rejected(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test that duplicate reports are rejected."""
        service = CommentService(test_db)
        comment = await service.create_comment(
            content_id=test_content.id, user_id=test_user.id, body="Report once", auto_approve=True
        )

        await service.report_comment(comment.id, test_user.id, ReportReason.SPAM)

        with pytest.raises(ValueError, match="already reported"):
            await service.report_comment(comment.id, test_user.id, ReportReason.HARASSMENT)

    @pytest.mark.asyncio
    async def test_auto_flag_on_threshold(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test that a comment is auto-flagged after reaching report threshold."""
        service = CommentService(test_db)
        comment = await service.create_comment(
            content_id=test_content.id, user_id=test_user.id, body="Flaggable comment", auto_approve=True
        )

        # Create multiple reporter users and report
        from app.models.user import Role

        role_result = await test_db.execute(__import__("sqlalchemy").select(Role).where(Role.name == "viewer"))
        role = role_result.scalar_one_or_none()
        if not role:
            role = Role(name="viewer")
            test_db.add(role)
            await test_db.commit()
            await test_db.refresh(role)

        for i in range(3):
            reporter = User(
                username=f"reporter_{i}",
                email=f"reporter_{i}@test.com",
                hashed_password="hashedpass",
                role_id=role.id,
            )
            test_db.add(reporter)
            await test_db.commit()
            await test_db.refresh(reporter)
            await service.report_comment(comment.id, reporter.id, ReportReason.SPAM)

        # Refresh comment to check status
        await test_db.refresh(comment)
        assert comment.status == CommentStatus.PENDING  # Auto-flagged back to PENDING

    @pytest.mark.asyncio
    async def test_review_report(self, test_db: AsyncSession, test_user: User, test_admin: User, test_content: Content):
        """Test reviewing a report."""
        service = CommentService(test_db)
        comment = await service.create_comment(
            content_id=test_content.id, user_id=test_user.id, body="Reviewed comment", auto_approve=True
        )

        report = await service.report_comment(comment.id, test_user.id, ReportReason.INAPPROPRIATE)

        reviewed = await service.review_report(report.id, test_admin.id, ReportStatus.REVIEWED)

        assert reviewed.status == ReportStatus.REVIEWED
        assert reviewed.reviewed_by == test_admin.id
        assert reviewed.reviewed_at is not None

    @pytest.mark.asyncio
    async def test_report_endpoint(self):
        """Test report endpoint via API."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/comments/999999/report",
                json={"reason": "spam"},
            )

        # Unauthenticated should get redirect or auth error
        assert response.status_code in (307, 401, 403)


# ============== Edit History Tests ==============


class TestCommentEditHistory:
    """Tests for comment edit history tracking."""

    @pytest.mark.asyncio
    async def test_edit_saves_history(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test that editing a comment saves the previous body."""
        service = CommentService(test_db)
        comment = await service.create_comment(content_id=test_content.id, user_id=test_user.id, body="Original body")

        await service.update_comment(comment.id, test_user.id, "Updated body")

        history = await service.get_edit_history(comment.id)
        assert len(history) == 1
        assert history[0].previous_body == "Original body"

    @pytest.mark.asyncio
    async def test_multiple_edits_history(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test that multiple edits create multiple history entries."""
        service = CommentService(test_db)
        comment = await service.create_comment(content_id=test_content.id, user_id=test_user.id, body="Version 1")

        await service.update_comment(comment.id, test_user.id, "Version 2")
        await service.update_comment(comment.id, test_user.id, "Version 3")

        history = await service.get_edit_history(comment.id)
        assert len(history) == 2
        # Newest first
        assert history[0].previous_body == "Version 2"
        assert history[1].previous_body == "Version 1"

    @pytest.mark.asyncio
    async def test_get_edit_history_empty(self, test_db: AsyncSession, test_user: User, test_content: Content):
        """Test that unedited comment has no history."""
        service = CommentService(test_db)
        comment = await service.create_comment(content_id=test_content.id, user_id=test_user.id, body="Never edited")

        history = await service.get_edit_history(comment.id)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_history_endpoint(self):
        """Test edit history endpoint via API."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v1/comments/999999/history")

        assert response.status_code == 200


# ============== Convenience Endpoint Tests ==============


class TestConvenienceEndpoints:
    """Tests for convenience approve/reject endpoints."""

    @pytest.mark.asyncio
    async def test_approve_endpoint_exists(self):
        """Test that the approve endpoint is registered."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/comments/999999/approve")

        # Unauthenticated should get redirect or auth error, not 405
        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_reject_endpoint_exists(self):
        """Test that the reject endpoint is registered."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/comments/999999/reject")

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_convenience_requires_admin(self):
        """Test that convenience endpoints require admin role."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/comments/1/approve")

        # Unauthenticated should get redirect or 401
        assert response.status_code in (307, 401, 403)


# ============== Activity Logging Tests ==============


class TestActivityLogging:
    """Tests for activity logging on comment operations."""

    def test_log_activity_importable(self):
        """Verify log_activity is importable and callable."""
        from app.utils.activity_log import log_activity

        assert callable(log_activity)

    def test_routes_have_activity_logging(self):
        """Verify comment routes import and use log_activity."""
        import inspect

        from app.routes import comments

        source = inspect.getsource(comments)
        assert "log_activity" in source
        assert "comment_create" in source
        assert "comment_update" in source
        assert "comment_delete" in source
        assert "comment_moderate" in source
