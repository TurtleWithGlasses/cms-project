"""
Plugin Registry — Phase 6.2

PluginRegistry: in-process singleton that stores registered plugins and
dispatches hook events to subscribers.

Hooks are fire-and-forget: each subscriber's handle_hook() is awaited in
sequence; exceptions are caught, logged, and execution continues.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.plugins.base import PluginBase

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    In-process registry for CMS plugins.

    Stores registered plugins by name and maintains an index of hook
    subscriptions for efficient dispatch.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginBase] = {}
        self._hook_subscriptions: dict[str, list[PluginBase]] = defaultdict(list)

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, plugin: PluginBase) -> None:
        """Register a plugin and index its hook subscriptions."""
        self._plugins[plugin.meta.name] = plugin
        for hook in plugin.meta.hooks:
            self._hook_subscriptions[hook].append(plugin)
        logger.info("Plugin registered: %s v%s", plugin.meta.name, plugin.meta.version)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, name: str) -> PluginBase | None:
        """Return the plugin with the given name, or None if not registered."""
        return self._plugins.get(name)

    def all_plugins(self) -> list[PluginBase]:
        """Return all registered plugins in registration order."""
        return list(self._plugins.values())

    def is_registered(self, name: str) -> bool:
        """Return True if a plugin with the given name has been registered."""
        return name in self._plugins

    # ── Hook dispatch ─────────────────────────────────────────────────────────

    async def fire_hook(self, hook_name: str, payload: dict[str, Any]) -> list[Any]:
        """
        Fire a hook to all subscribing plugins.

        Each plugin's handle_hook() is called in turn.  Exceptions are caught
        and logged — a misbehaving plugin never prevents others from running or
        blocks request processing.

        Args:
            hook_name: Hook constant from app.plugins.hooks.
            payload:   Arbitrary data passed to each subscriber.

        Returns:
            List of return values from each subscriber (None for no-ops).
        """
        results: list[Any] = []
        for plugin in self._hook_subscriptions.get(hook_name, []):
            try:
                result = await plugin.handle_hook(hook_name, payload)
                results.append(result)
            except Exception as exc:
                logger.warning(
                    "Plugin %s hook %s raised: %s",
                    plugin.meta.name,
                    hook_name,
                    exc,
                )
        return results


# ── Global singleton ──────────────────────────────────────────────────────────
# Import this wherever you need to fire hooks or inspect registered plugins.
plugin_registry = PluginRegistry()
