"""Tests for team management functionality."""

import pytest

from app.models.team import InvitationStatus, Team, TeamInvitation, TeamMember, TeamRole


class TestTeamModels:
    """Test Team model and related models."""

    def test_team_creation(self):
        """Test creating a Team instance."""
        team = Team(
            name="Engineering Team",
            slug="engineering-team",
            description="Backend developers",
        )
        assert team.name == "Engineering Team"
        assert team.slug == "engineering-team"
        assert team.description == "Backend developers"

    def test_team_defaults(self):
        """Test Team default values."""
        team = Team(name="Test", slug="test")
        assert team.is_active is True
        assert team.allow_member_invite is False
        assert team.default_member_role == TeamRole.MEMBER

    def test_team_member_creation(self):
        """Test creating a TeamMember instance."""
        member = TeamMember(
            team_id=1,
            user_id=1,
            role=TeamRole.ADMIN,
        )
        assert member.team_id == 1
        assert member.user_id == 1
        assert member.role == TeamRole.ADMIN

    def test_team_invitation_creation(self):
        """Test creating a TeamInvitation instance."""
        invitation = TeamInvitation(
            team_id=1,
            email="test@example.com",
            role=TeamRole.MEMBER,
            token="abc123",
        )
        assert invitation.email == "test@example.com"
        assert invitation.status == InvitationStatus.PENDING
        assert invitation.token == "abc123"


class TestTeamRoles:
    """Test TeamRole enum."""

    def test_role_values(self):
        """Test all role values exist."""
        assert TeamRole.OWNER.value == "owner"
        assert TeamRole.ADMIN.value == "admin"
        assert TeamRole.MEMBER.value == "member"
        assert TeamRole.VIEWER.value == "viewer"

    def test_role_comparison(self):
        """Test role comparison."""
        assert TeamRole.OWNER != TeamRole.ADMIN
        assert TeamRole.MEMBER == TeamRole.MEMBER


class TestInvitationStatus:
    """Test InvitationStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert InvitationStatus.PENDING.value == "pending"
        assert InvitationStatus.ACCEPTED.value == "accepted"
        assert InvitationStatus.DECLINED.value == "declined"
        assert InvitationStatus.EXPIRED.value == "expired"


class TestTeamService:
    """Test team service functions."""

    def test_generate_slug(self):
        """Test slug generation."""
        from app.services.team_service import generate_slug

        assert generate_slug("Engineering Team") == "engineering-team"
        assert generate_slug("Test!@#$%") == "test"
        assert generate_slug("Multiple   Spaces") == "multiple-spaces"
        assert generate_slug("  Trim  ") == "trim"
