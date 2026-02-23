"""
SEO Plugin — Phase 6.2

Adapter wrapping the existing SEO functionality:
  - app/routes/seo.py        (sitemap.xml, robots.txt, RSS/Atom feeds)
  - app/services/seo_service.py (SEOService, JSON-LD, OG tags)

Hook subscriptions:
  - content.published  → log sitemap invalidation signal
  - content.updated    → log sitemap invalidation signal
  - content.deleted    → log sitemap invalidation signal
"""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.base import PluginBase, PluginMeta
from app.plugins.hooks import HOOK_CONTENT_DELETED, HOOK_CONTENT_PUBLISHED, HOOK_CONTENT_UPDATED

logger = logging.getLogger(__name__)

_META = PluginMeta(
    name="seo",
    version="1.0.0",
    description=(
        "SEO tooling — sitemap.xml, RSS/Atom feeds, robots.txt, "
        "JSON-LD structured data, Open Graph and Twitter Card metadata"
    ),
    hooks=[HOOK_CONTENT_PUBLISHED, HOOK_CONTENT_UPDATED, HOOK_CONTENT_DELETED],
    config_schema={
        "json_ld_enabled": {"type": "boolean", "default": True},
        "sitemap_include_drafts": {"type": "boolean", "default": False},
    },
)


class SEOPlugin(PluginBase):
    """SEO plugin adapter — wraps existing seo_service and seo routes."""

    @property
    def meta(self) -> PluginMeta:
        return _META

    async def on_load(self, config: dict[str, Any]) -> None:
        self._config = config
        logger.debug("SEOPlugin loaded (json_ld_enabled=%s)", config.get("json_ld_enabled", True))

    async def handle_hook(self, hook_name: str, payload: dict[str, Any]) -> None:
        if hook_name in (HOOK_CONTENT_PUBLISHED, HOOK_CONTENT_UPDATED, HOOK_CONTENT_DELETED):
            logger.debug(
                "SEOPlugin: %s — sitemap cache invalidation signalled (content_id=%s)",
                hook_name,
                payload.get("content_id"),
            )
        return None
