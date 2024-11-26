from sqlalchemy import Column, Integer, String, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum

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
    role = relationship("Role", lazy="joined")
    
    # Update the relationship to remove `delete-orphan`
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        single_parent=True  # Enforces strict ownership
    )

    contents = relationship("Content", back_populates="author")
    activity_logs = relationship("ActivityLog", back_populates="user", foreign_keys="ActivityLog.user_id")
    target_activity_logs = relationship("ActivityLog", foreign_keys="ActivityLog.target_user_id", overlaps="activity_logs")