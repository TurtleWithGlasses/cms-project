"""Team and team membership models for collaborative content management."""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class TeamRole(str, enum.Enum):
    """Role within a team."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InvitationStatus(str, enum.Enum):
    """Status of team invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class Team(Base):
    """Team/organization for grouping users."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Hierarchy support
    parent_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    # Creator/owner
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    allow_member_invite = Column(Boolean, default=False, nullable=False)
    default_member_role = Column(Enum(TeamRole), default=TeamRole.MEMBER, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    parent_team = relationship("Team", remote_side=[id], backref="sub_teams")
    created_by = relationship("User", foreign_keys=[created_by_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    invitations = relationship("TeamInvitation", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """Membership association between users and teams."""

    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Role within team
    role = Column(Enum(TeamRole), default=TeamRole.MEMBER, nullable=False)

    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", backref="team_memberships")


class TeamInvitation(Base):
    """Invitation to join a team."""

    __tablename__ = "team_invitations"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)

    # Invitee info (email for external, user_id for existing users)
    email = Column(String(255), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Invitation details
    role = Column(Enum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    message = Column(Text, nullable=True)

    # Who sent the invitation
    invited_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    responded_at = Column(DateTime, nullable=True)

    # Relationships
    team = relationship("Team", back_populates="invitations")
    user = relationship("User", foreign_keys=[user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])
