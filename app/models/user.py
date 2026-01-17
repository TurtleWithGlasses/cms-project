import enum

from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


# Enum for predefined roles
class RoleEnum(str, enum.Enum):
    user = "user"
    admin = "admin"
    superadmin = "superadmin"
    manager = "manager"
    editor = "editor"


# Role model
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Use Enum for role names
    permissions = Column(JSON, nullable=False)  # Store permissions in JSON format
    users = relationship("User", back_populates="role")


# User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    role = relationship("Role", lazy="selectin")

    # Update the relationship to remove `delete-orphan`
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        single_parent=True,  # Enforces strict ownership
    )

    contents = relationship("Content", back_populates="author")
    activity_logs = relationship("ActivityLog", back_populates="user", foreign_keys="ActivityLog.user_id")
    target_activity_logs = relationship(
        "ActivityLog", foreign_keys="ActivityLog.target_user_id", overlaps="activity_logs"
    )
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    uploaded_media = relationship("Media", back_populates="uploader", cascade="all, delete-orphan")

    # Index for role-based queries
    __table_args__ = (Index("ix_users_role_id", "role_id"),)
