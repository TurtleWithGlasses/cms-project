"""
ConsentRecord model for GDPR consent tracking (Article 7).

Records each explicit consent action by a user, providing a complete
timestamped audit trail of policy acceptance.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String

from app.database import Base


class ConsentRecord(Base):
    """
    Tracks user consent to privacy policies and data processing activities.

    Each row represents a single consent event — duplicates are intentional
    and expected (every explicit consent action is recorded as a fact).
    """

    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_version = Column(String(20), nullable=False)
    consented_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # IPv6 addresses can be up to 39 chars; 45 allows for mapped IPv4 addresses
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    # Valid values: "privacy_policy", "marketing", "analytics"
    consent_type = Column(String(50), nullable=False, default="privacy_policy")

    __table_args__ = (
        Index("idx_consent_user_type", "user_id", "consent_type"),
        Index("idx_consent_user_version", "user_id", "policy_version"),
    )
