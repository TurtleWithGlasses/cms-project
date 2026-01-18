"""Content template models for reusable content structures."""

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


class TemplateStatus(str, enum.Enum):
    """Status of a content template."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class FieldType(str, enum.Enum):
    """Types of template fields."""

    TEXT = "text"
    TEXTAREA = "textarea"
    RICHTEXT = "richtext"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"
    IMAGE = "image"
    FILE = "file"
    URL = "url"
    EMAIL = "email"
    JSON = "json"
    REFERENCE = "reference"  # Reference to other content


class ContentTemplate(Base):
    """Reusable content template with defined structure."""

    __tablename__ = "content_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Icon name for UI

    # Template status
    status = Column(Enum(TemplateStatus), default=TemplateStatus.DRAFT, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    # Default values for content created from this template
    default_status = Column(String(20), default="draft", nullable=False)

    # Creator
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    fields = relationship(
        "TemplateField",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateField.order",
    )
    revisions = relationship(
        "TemplateRevision",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateRevision.version.desc()",
    )


class TemplateField(Base):
    """Field definition within a content template."""

    __tablename__ = "template_fields"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("content_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Field identification
    name = Column(String(100), nullable=False)  # Internal name
    label = Column(String(100), nullable=False)  # Display label
    description = Column(Text, nullable=True)  # Help text

    # Field type and configuration
    field_type = Column(Enum(FieldType), nullable=False)
    is_required = Column(Boolean, default=False, nullable=False)
    is_unique = Column(Boolean, default=False, nullable=False)
    is_searchable = Column(Boolean, default=True, nullable=False)

    # Ordering
    order = Column(Integer, default=0, nullable=False)

    # Default value (JSON encoded)
    default_value = Column(Text, nullable=True)

    # Validation rules (JSON encoded)
    # e.g., {"min_length": 10, "max_length": 500, "pattern": "^[a-z]+$"}
    validation_rules = Column(Text, nullable=True)

    # Options for select/multiselect (JSON array)
    # e.g., ["option1", "option2", "option3"]
    options = Column(Text, nullable=True)

    # For reference fields - which content type to reference
    reference_template_id = Column(Integer, ForeignKey("content_templates.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    template = relationship("ContentTemplate", back_populates="fields", foreign_keys=[template_id])
    reference_template = relationship("ContentTemplate", foreign_keys=[reference_template_id])


class TemplateRevision(Base):
    """Version history for content templates."""

    __tablename__ = "template_revisions"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("content_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Version info
    version = Column(Integer, nullable=False)
    change_summary = Column(String(500), nullable=True)

    # Snapshot of template at this version (JSON)
    snapshot = Column(Text, nullable=False)

    # Who made the change
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    template = relationship("ContentTemplate", back_populates="revisions")
    created_by = relationship("User")
