"""
Plugin Loader — Phase 6.2

Handles reading/writing plugin configuration from `data/plugins_config.json`
and initialising all built-in plugins at application startup.

Mirrors the _load_settings / _save_settings pattern from app/routes/settings.py.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)

# ── Config file location ──────────────────────────────────────────────────────
_PLUGINS_CONFIG_FILE = Path("data/plugins_config.json")

# ── Default plugin config (all built-in plugins enabled) ─────────────────────
_DEFAULT_CONFIG: dict[str, dict[str, Any]] = {
    "seo": {"enabled": True},
    "analytics": {"enabled": True},
    "social": {"enabled": True},
    "custom_fields": {"enabled": True},
}


# ── Config I/O ────────────────────────────────────────────────────────────────


def load_plugins_config() -> dict[str, dict[str, Any]]:
    """
    Load plugin configuration from disk.

    Returns defaults if the file does not exist or cannot be parsed.
    """
    if _PLUGINS_CONFIG_FILE.exists():
        try:
            return json.loads(_PLUGINS_CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read plugins config: %s", exc)
    return copy.deepcopy(_DEFAULT_CONFIG)


def save_plugins_config(config: dict[str, dict[str, Any]]) -> None:
    """Persist plugin configuration to disk."""
    _PLUGINS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PLUGINS_CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Startup initialisation ────────────────────────────────────────────────────


async def initialize_plugins(registry: PluginRegistry) -> None:
    """
    Load and register all built-in plugins.

    Called from main.py lifespan() after install_retention_policy().
    Deferred imports inside this function prevent circular imports at module
    load time (same pattern as app/utils/audit_retention.py).
    """
    from app.plugins.analytics_plugin import AnalyticsPlugin
    from app.plugins.custom_fields_plugin import CustomFieldsPlugin
    from app.plugins.seo_plugin import SEOPlugin
    from app.plugins.social_plugin import SocialPlugin

    config = load_plugins_config()

    for plugin_class in [SEOPlugin, AnalyticsPlugin, SocialPlugin, CustomFieldsPlugin]:
        plugin = plugin_class()
        plugin_config = config.get(plugin.meta.name, {})
        await plugin.on_load(plugin_config)
        registry.register(plugin)

    logger.info("Plugin initialisation complete — %d plugins loaded", len(config))
