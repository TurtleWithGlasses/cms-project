from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class RoleEnum(str, enum.Enum):
    user = "user"
    admin = "admin"
    superadmin = "superadmin"
    manager = "manager"
    editor = "editor"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String)
    email = Column(String(100), unique=True, index=True)
    role = Column(String(20), default="user")

    contents = relationship("Content", back_populates="author")
    activity_logs = relationship("ActivityLog", back_populates="user", foreign_keys="ActivityLog.user_id")
    target_activity_logs = relationship("ActivityLog", foreign_keys="ActivityLog.target_user_id", overlaps="activity_logs")
