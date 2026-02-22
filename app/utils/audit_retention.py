"""
Audit Log Retention Policy

Polls and prunes ActivityLog entries older than the configured retention period.
Runs as a recurring APScheduler job — zero per-request overhead.

Mirrors the pattern from app/utils/pool_monitor.py exactly.
"""

import logging

from apscheduler.triggers.interval import IntervalTrigger

from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def prune_old_activity_logs(retention_days: int) -> int:
    """
    Delete ActivityLog rows older than retention_days.

    Opens its own DB session (same pattern as log_activity() in activity_log.py).
    Returns the count of deleted rows, or 0 on failure (graceful degradation).
    """
    # Deferred import avoids circular dependency between utils and services
    from app.services.gdpr_service import enforce_data_retention

    async with AsyncSessionLocal() as db:
        try:
            deleted = await enforce_data_retention(retention_days, db)
            return deleted
        except Exception as exc:
            logger.warning("audit_retention: prune failed: %s", exc)
            return 0


def install_retention_policy(
    scheduler,
    retention_days: int,
    interval_hours: int = 24,
) -> None:
    """
    Register the audit-log retention pruning job with the shared APScheduler instance.

    Args:
        scheduler: The application's AsyncIOScheduler (from app.scheduler).
        retention_days: ActivityLog rows older than this many days are deleted.
        interval_hours: How often to run (default: once daily).
    """
    scheduler.add_job(
        prune_old_activity_logs,
        trigger=IntervalTrigger(hours=interval_hours),
        args=[retention_days],
        id="audit_retention",
        replace_existing=True,
        max_instances=1,
    )
    logger.info(
        "audit_retention: installed (retention=%d days, interval=%dh)",
        retention_days,
        interval_hours,
    )
