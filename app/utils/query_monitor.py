"""
Database Query Monitor

Automatic slow query logging and Prometheus instrumentation
via SQLAlchemy event listeners. Attach once at startup to
instrument ALL queries without per-service decorators.
"""

import logging
import time

from sqlalchemy import event

from app.utils.metrics import DB_QUERIES_TOTAL, DB_QUERY_DURATION_SECONDS

logger = logging.getLogger(__name__)


def install_query_monitor(engine, slow_threshold_ms: int = 100) -> None:
    """Install event listeners on the async engine for query monitoring."""
    sync_engine = engine.sync_engine

    @event.listens_for(sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info["query_start_time"] = time.perf_counter()

    @event.listens_for(sync_engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start = conn.info.pop("query_start_time", None)
        if start is None:
            return
        duration = time.perf_counter() - start
        duration_ms = duration * 1000

        # Determine operation type from statement
        trimmed = statement.strip()
        operation = trimmed.split()[0].lower() if trimmed else "unknown"

        DB_QUERIES_TOTAL.labels(operation=operation).inc()
        DB_QUERY_DURATION_SECONDS.labels(operation=operation).observe(duration)

        if duration_ms > slow_threshold_ms:
            logger.warning(
                "Slow query detected (%.1fms): %s",
                duration_ms,
                trimmed[:200],
            )
