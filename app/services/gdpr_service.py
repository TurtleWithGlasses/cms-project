"""
GDPR Compliance Service

Provides consent management (Article 7) and data retention enforcement.
All functions are async and accept an injected AsyncSession.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.consent_record import ConsentRecord

logger = logging.getLogger(__name__)


async def record_consent(
    user_id: int,
    consent_type: str,
    policy_version: str,
    ip_address: str | None,
    user_agent: str | None,
    db: AsyncSession,
) -> ConsentRecord:
    """
    Insert a new consent record for the user (GDPR Article 7).

    Every explicit consent action is recorded as a timestamped fact —
    duplicates are intentional to preserve the full audit trail.
    """
    record = ConsentRecord(
        user_id=user_id,
        consent_type=consent_type,
        policy_version=policy_version,
        consented_at=datetime.now(timezone.utc),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    logger.info(
        "Consent recorded: user=%d type=%s version=%s",
        user_id,
        consent_type,
        policy_version,
    )
    return record


async def get_consent_history(
    user_id: int,
    db: AsyncSession,
) -> list[ConsentRecord]:
    """Return all consent records for the user, newest first."""
    result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == user_id).order_by(ConsentRecord.consented_at.desc())
    )
    return list(result.scalars().all())


async def has_valid_consent(
    user_id: int,
    consent_type: str,
    policy_version: str,
    db: AsyncSession,
) -> bool:
    """
    Return True if the user has at least one consent record for the given
    consent_type and policy_version.
    """
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.policy_version == policy_version,
        )
    )
    return result.scalars().first() is not None


async def enforce_data_retention(
    retention_days: int,
    db: AsyncSession,
) -> int:
    """
    Delete ActivityLog rows older than retention_days using a single
    Core-level DELETE statement for efficiency.

    Returns the count of deleted rows.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    result = await db.execute(delete(ActivityLog).where(ActivityLog.timestamp < cutoff))
    await db.commit()
    deleted_count = result.rowcount
    logger.info(
        "audit_retention: deleted %d ActivityLog rows older than %s (%d days)",
        deleted_count,
        cutoff.isoformat(),
        retention_days,
    )
    return deleted_count
