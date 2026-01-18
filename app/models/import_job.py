"""Import job models for tracking content and user imports."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ImportType(str, enum.Enum):
    """Type of data being imported."""

    CONTENT = "content"
    USERS = "users"
    CATEGORIES = "categories"
    TAGS = "tags"
    MEDIA = "media"
    MIXED = "mixed"


class ImportFormat(str, enum.Enum):
    """Format of the import file."""

    JSON = "json"
    CSV = "csv"
    XML = "xml"


class ImportStatus(str, enum.Enum):
    """Status of an import job."""

    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # Completed with some errors


class DuplicateHandling(str, enum.Enum):
    """How to handle duplicate records during import."""

    SKIP = "skip"
    UPDATE = "update"
    CREATE_NEW = "create_new"
    FAIL = "fail"


class ImportJob(Base):
    """Track import operations with progress and results."""

    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # Job identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Import configuration
    import_type = Column(Enum(ImportType), nullable=False)
    import_format = Column(Enum(ImportFormat), nullable=False)
    status = Column(Enum(ImportStatus), default=ImportStatus.PENDING, nullable=False)
    duplicate_handling = Column(Enum(DuplicateHandling), default=DuplicateHandling.SKIP, nullable=False)

    # File information
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes

    # Progress tracking
    total_records = Column(Integer, default=0, nullable=False)
    processed_records = Column(Integer, default=0, nullable=False)
    successful_records = Column(Integer, default=0, nullable=False)
    failed_records = Column(Integer, default=0, nullable=False)
    skipped_records = Column(Integer, default=0, nullable=False)

    # Field mapping (JSON - maps source fields to destination fields)
    field_mapping = Column(Text, nullable=True)

    # Error log (JSON array of error details)
    error_log = Column(Text, nullable=True)

    # Results summary (JSON)
    results_summary = Column(Text, nullable=True)

    # Who initiated the import
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    created_by = relationship("User", backref="import_jobs")
    records = relationship("ImportRecord", back_populates="import_job", cascade="all, delete-orphan")


class ImportRecord(Base):
    """Individual record within an import job."""

    __tablename__ = "import_records"

    id = Column(Integer, primary_key=True, index=True)
    import_job_id = Column(
        Integer,
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Record identification
    row_number = Column(Integer, nullable=False)
    source_id = Column(String(255), nullable=True)  # Original ID from source

    # Result
    status = Column(Enum(ImportStatus), default=ImportStatus.PENDING, nullable=False)
    created_record_id = Column(Integer, nullable=True)  # ID of created/updated record
    created_record_type = Column(String(50), nullable=True)  # content, user, etc.

    # Original data (JSON)
    source_data = Column(Text, nullable=True)

    # Error details if failed
    error_message = Column(Text, nullable=True)

    # Timestamps
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    import_job = relationship("ImportJob", back_populates="records")


class ExportJob(Base):
    """Track export operations."""

    __tablename__ = "export_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # Job identification
    name = Column(String(255), nullable=False)

    # Export configuration
    export_type = Column(Enum(ImportType), nullable=False)  # Reuse ImportType
    export_format = Column(Enum(ImportFormat), nullable=False)
    status = Column(Enum(ImportStatus), default=ImportStatus.PENDING, nullable=False)

    # Filters applied (JSON)
    filters = Column(Text, nullable=True)

    # Result file
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)

    # Progress
    total_records = Column(Integer, default=0, nullable=False)
    exported_records = Column(Integer, default=0, nullable=False)

    # Who initiated the export
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # When the export file expires

    # Relationships
    created_by = relationship("User", backref="export_jobs")
