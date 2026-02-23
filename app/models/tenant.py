"""
Tenant model — Phase 6.1 Multi-Tenancy foundation.

Each Tenant represents an isolated organisation (customer account).
Row-level isolation via tenant_id FK on per-resource tables (Phase 6.2+).
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class TenantStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    deleted = "deleted"


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)  # URL-safe, e.g. "acme"
    domain = Column(String(253), nullable=True, unique=True)  # optional custom domain, e.g. "cms.acme.com"
    status = Column(String(20), nullable=False, default=TenantStatus.active.value)
    plan = Column(String(50), nullable=True)  # "free" | "pro" | "enterprise"
    # Use metadata_ as Python attr to avoid shadowing SQLAlchemy Base.metadata
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationship back to the creating user (no back_populates — avoids circular import)
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="select")

    __table_args__ = (
        Index("idx_tenant_slug", "slug"),
        Index("idx_tenant_status", "status"),
    )
