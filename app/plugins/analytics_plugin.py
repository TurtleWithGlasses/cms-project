"""
Analytics Plugin — Phase 6.2

Adapter wrapping the existing Analytics functionality:
  - app/routes/analytics.py       (dashboard, content stats, session analytics)
  - app/services/analytics_service.py (view tracking, popular content, GA4/Plausible proxy)

Hook subscriptions:
  - content.published → log analytics event signal
  - user.created      → log user registration analytics signal
"""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.base import PluginBase, PluginMeta
from app.plugins.hooks import HOOK_CONTENT_PUBLISHED, HOOK_USER_CREATED

logger = logging.getLogger(__name__)

_META = PluginMeta(
    name="analytics",
    version="1.0.0",
    description=(
        "Analytics and metrics — page views, popular content rankings, "
        "session analytics, GA4/Plausible integration, UTM tracking"
    ),
    hooks=[HOOK_CONTENT_PUBLISHED, HOOK_USER_CREATED],
    config_schema={
        "retention_days": {"type": "integer", "default": 90},
        "track_anonymous": {"type": "boolean", "default": True},
    },
)


class AnalyticsPlugin(PluginBase):
    """Analytics plugin adapter — wraps existing analytics_service and analytics routes."""

    @property
    def meta(self) -> PluginMeta:
        return _META

    async def on_load(self, config: dict[str, Any]) -> None:
        self._config = config
        logger.debug(
            "AnalyticsPlugin loaded (retention_days=%s)",
            config.get("retention_days", 90),
        )

    async def handle_hook(self, hook_name: str, payload: dict[str, Any]) -> None:
        if hook_name == HOOK_CONTENT_PUBLISHED:
            logger.debug(
                "AnalyticsPlugin: content.published — analytics event queued (content_id=%s)",
                payload.get("content_id"),
            )
        elif hook_name == HOOK_USER_CREATED:
            logger.debug(
                "AnalyticsPlugin: user.created — registration event queued (user_id=%s)",
                payload.get("user_id"),
            )
        return None
