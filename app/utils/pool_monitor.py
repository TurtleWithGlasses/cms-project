"""
Connection Pool Monitor

Polls SQLAlchemy connection pool statistics every N seconds and pushes
the values into Prometheus gauges.  Runs as a recurring APScheduler job
so there is zero per-request overhead.

Attach once at startup via install_pool_monitor().
"""

import logging

from apscheduler.triggers.interval import IntervalTrigger

from app.database import get_pool_stats
from app.utils.metrics import update_pool_metrics

logger = logging.getLogger(__name__)


async def _poll_pool_metrics() -> None:
    """Scheduled job: scrape pool stats and update Prometheus gauges."""
    try:
        stats = get_pool_stats()
        update_pool_metrics("primary", stats["primary"])
        update_pool_metrics("replica", stats["replica"])
    except Exception as exc:
        logger.warning("pool_monitor: failed to collect pool stats: %s", exc)


def install_pool_monitor(scheduler, interval_seconds: int = 15) -> None:
    """
    Register the pool-metrics polling job with the shared APScheduler instance.

    Args:
        scheduler: The application's AsyncIOScheduler (from app.scheduler).
        interval_seconds: How often to scrape pool stats (default 15 s).
    """
    scheduler.add_job(
        _poll_pool_metrics,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id="pool_monitor",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("pool_monitor: installed (interval=%ds)", interval_seconds)
