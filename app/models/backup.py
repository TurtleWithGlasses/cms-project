"""
Backup Model

Stores metadata about database backups for tracking and management.
"""

from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class BackupStatus(str, Enum):
    """Backup status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BackupType(str, Enum):
    """Backup type enumeration."""

    FULL = "full"  # Full database backup
    INCREMENTAL = "incremental"  # Incremental backup
    CONTENT_ONLY = "content_only"  # Only content tables
    MEDIA_ONLY = "media_only"  # Only media files


class Backup(Base):
    """
    Backup model for tracking database backups.

    Stores metadata about each backup including:
    - Backup file location and size
    - Backup type and status
    - Creation and completion timestamps
    - Optional description and error messages
    """

    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # Size in bytes

    backup_type = Column(SQLEnum(BackupType), default=BackupType.FULL, nullable=False)
    status = Column(SQLEnum(BackupStatus), default=BackupStatus.PENDING, nullable=False)

    description = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # What's included in the backup
    include_database = Column(Boolean, default=True)
    include_media = Column(Boolean, default=True)
    include_config = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Who created the backup
    created_by_id = Column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<Backup(id={self.id}, filename='{self.filename}', status={self.status.value})>"

    @property
    def duration_seconds(self) -> float | None:
        """Calculate backup duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def file_size_mb(self) -> float | None:
        """Return file size in megabytes."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None


class BackupSchedule(Base):
    """
    Backup schedule configuration.

    Stores the automated backup schedule settings.
    Only one active schedule should exist at a time.
    """

    __tablename__ = "backup_schedules"

    id = Column(Integer, primary_key=True, index=True)

    enabled = Column(Boolean, default=False)
    frequency = Column(String(50), default="daily")  # daily, weekly, monthly
    time_of_day = Column(String(10), default="02:00")  # HH:MM format
    day_of_week = Column(Integer, nullable=True)  # 0-6 for weekly (0=Monday)
    day_of_month = Column(Integer, nullable=True)  # 1-31 for monthly

    # Retention settings
    retention_days = Column(Integer, default=30)  # Keep backups for N days
    max_backups = Column(Integer, default=10)  # Maximum number of backups to keep

    # Backup options
    backup_type = Column(SQLEnum(BackupType), default=BackupType.FULL)
    include_database = Column(Boolean, default=True)
    include_media = Column(Boolean, default=True)
    include_config = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BackupSchedule(id={self.id}, enabled={self.enabled}, frequency='{self.frequency}')>"
