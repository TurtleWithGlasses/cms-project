"""
CMS Plugin System — Phase 6.2

Public API for the plugin system:
    PluginMeta      — plugin metadata dataclass
    PluginBase      — abstract base class for all plugins
    PluginRegistry  — registry + hook dispatcher
    plugin_registry — global singleton registry instance
"""

from .base import PluginBase, PluginMeta
from .registry import PluginRegistry, plugin_registry

__all__ = ["PluginBase", "PluginMeta", "PluginRegistry", "plugin_registry"]
