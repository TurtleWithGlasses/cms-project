"""
Plugin Base Classes — Phase 6.2

PluginMeta: declarative metadata for a plugin (name, version, hooks, config schema).
PluginBase: abstract base class all plugins must subclass.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginMeta:
    """
    Declarative metadata describing a plugin.

    Attributes:
        name:          Machine-readable slug, e.g. "seo", "analytics".
        version:       Semver string, e.g. "1.0.0".
        description:   Human-readable description shown in admin UI.
        author:        Plugin author (defaults to "CMS Core Team").
        hooks:         List of hook names this plugin subscribes to.
        config_schema: JSON Schema fragments describing configurable options
                       (used by admin UI for form generation).
    """

    name: str
    version: str
    description: str
    author: str = "CMS Core Team"
    hooks: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)


class PluginBase(ABC):
    """
    Abstract base class for all CMS plugins.

    Subclasses must implement the `meta` property.
    All lifecycle methods have default no-op implementations so subclasses only
    override what they need.
    """

    @property
    @abstractmethod
    def meta(self) -> PluginMeta:
        """Return the plugin's metadata."""
        ...

    async def on_load(self, config: dict[str, Any]) -> None:  # noqa: B027
        """
        Called once at startup with the plugin's persisted config dict.

        Override to perform one-time initialisation (e.g. store config,
        warm caches, register scheduled jobs).
        """

    async def on_unload(self) -> None:  # noqa: B027
        """
        Called when the plugin is disabled at runtime or the app shuts down.

        Override to release resources (e.g. cancel tasks, close connections).
        """

    async def handle_hook(self, hook_name: str, payload: dict[str, Any]) -> Any:
        """
        Receive and process a hook event.

        Called by PluginRegistry.fire_hook() for each hook the plugin
        declared in PluginMeta.hooks.  Default implementation is a no-op.

        Args:
            hook_name: The hook constant, e.g. "content.published".
            payload:   Arbitrary data provided by the hook dispatcher.

        Returns:
            Any value (ignored by fire_hook unless needed by caller).
        """
        return None
