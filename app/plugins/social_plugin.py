"""
Social Plugin — Phase 6.2

Adapter wrapping the existing Social Sharing functionality:
  - app/routes/social.py        (share URL endpoints, OG/Twitter metadata)
  - app/services/social_service.py (SocialSharingService, SocialPostingService stub)

Hook subscriptions:
  - content.published → log social auto-post signal (stub — posting not invoked unless configured)
"""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.base import PluginBase, PluginMeta
from app.plugins.hooks import HOOK_CONTENT_PUBLISHED

logger = logging.getLogger(__name__)

_META = PluginMeta(
    name="social",
    version="1.0.0",
    description=(
        "Social sharing — share URL generation (Twitter, Facebook, LinkedIn, WhatsApp), "
        "Open Graph / Twitter Card metadata, JSON-LD structured data, auto-post stub"
    ),
    hooks=[HOOK_CONTENT_PUBLISHED],
    config_schema={
        "auto_post_enabled": {"type": "boolean", "default": False},
        "platforms": {
            "type": "array",
            "items": {"type": "string"},
            "default": ["twitter", "facebook", "linkedin"],
        },
    },
)


class SocialPlugin(PluginBase):
    """Social plugin adapter — wraps existing social_service and social routes."""

    @property
    def meta(self) -> PluginMeta:
        return _META

    async def on_load(self, config: dict[str, Any]) -> None:
        self._config = config
        logger.debug(
            "SocialPlugin loaded (auto_post_enabled=%s)",
            config.get("auto_post_enabled", False),
        )

    async def handle_hook(self, hook_name: str, payload: dict[str, Any]) -> None:
        if hook_name == HOOK_CONTENT_PUBLISHED:
            auto_post = self._config.get("auto_post_enabled", False)
            logger.debug(
                "SocialPlugin: content.published — social auto-post hook (content_id=%s, auto_post_enabled=%s)",
                payload.get("content_id"),
                auto_post,
            )
        return None
