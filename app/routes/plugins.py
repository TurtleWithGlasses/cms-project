"""
Plugin Administration Routes — Phase 6.2 Plugin System

All routes require admin or superadmin role.
Enable/disable/configure routes require superadmin.

GET  /api/v1/plugins          → list all registered plugins
GET  /api/v1/plugins/{name}   → get single plugin by name
POST /api/v1/plugins/{name}/enable  → enable plugin
POST /api/v1/plugins/{name}/disable → disable plugin
PUT  /api/v1/plugins/{name}/config  → update plugin config

No DB dependency — plugin state is stored in data/plugins_config.json.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import require_role
from app.models.user import User  # noqa: TC001
from app.plugins.base import PluginBase  # noqa: TC001
from app.plugins.loader import load_plugins_config, save_plugins_config
from app.plugins.registry import plugin_registry

router = APIRouter(tags=["Plugins"])
logger = logging.getLogger(__name__)


# ── Pydantic schemas ───────────────────────────────────────────────────────────


class PluginConfigUpdate(BaseModel):
    config: dict[str, Any]


class PluginResponse(BaseModel):
    name: str
    version: str
    description: str
    author: str
    enabled: bool
    hooks: list[str]
    config: dict[str, Any]
    config_schema: dict[str, Any]


# ── Helpers ────────────────────────────────────────────────────────────────────


def _build_response(plugin: PluginBase, all_config: dict[str, Any]) -> PluginResponse:
    plugin_config = all_config.get(plugin.meta.name, {})
    return PluginResponse(
        name=plugin.meta.name,
        version=plugin.meta.version,
        description=plugin.meta.description,
        author=plugin.meta.author,
        enabled=plugin_config.get("enabled", True),
        hooks=plugin.meta.hooks,
        config=plugin_config,
        config_schema=plugin.meta.config_schema,
    )


def _get_or_404(name: str) -> PluginBase:
    plugin = plugin_registry.get(name)
    if plugin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {name}",
        )
    return plugin


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[PluginResponse])
async def list_plugins(
    _current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> list[PluginResponse]:
    """List all registered plugins with their status and configuration (admin+)."""
    all_config = load_plugins_config()
    return [_build_response(p, all_config) for p in plugin_registry.all_plugins()]


@router.get("/{name}", response_model=PluginResponse)
async def get_plugin(
    name: str,
    _current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> PluginResponse:
    """Get a single plugin by name (admin+)."""
    plugin = _get_or_404(name)
    all_config = load_plugins_config()
    return _build_response(plugin, all_config)


@router.post("/{name}/enable", response_model=PluginResponse)
async def enable_plugin(
    name: str,
    _current_user: User = Depends(require_role(["superadmin"])),
) -> PluginResponse:
    """Enable a plugin by name (superadmin only)."""
    plugin = _get_or_404(name)
    all_config = load_plugins_config()
    plugin_config = all_config.get(name, {})
    plugin_config["enabled"] = True
    all_config[name] = plugin_config
    save_plugins_config(all_config)
    logger.info("Plugin enabled: %s", name)
    return _build_response(plugin, all_config)


@router.post("/{name}/disable", response_model=PluginResponse)
async def disable_plugin(
    name: str,
    _current_user: User = Depends(require_role(["superadmin"])),
) -> PluginResponse:
    """Disable a plugin by name (superadmin only)."""
    plugin = _get_or_404(name)
    all_config = load_plugins_config()
    plugin_config = all_config.get(name, {})
    plugin_config["enabled"] = False
    all_config[name] = plugin_config
    save_plugins_config(all_config)
    logger.info("Plugin disabled: %s", name)
    return _build_response(plugin, all_config)


@router.put("/{name}/config", response_model=PluginResponse)
async def update_plugin_config(
    name: str,
    payload: PluginConfigUpdate,
    _current_user: User = Depends(require_role(["superadmin"])),
) -> PluginResponse:
    """Update a plugin's configuration (superadmin only).

    Merges the provided config dict into the existing plugin config,
    preserving the `enabled` flag and any keys not present in the update.
    """
    plugin = _get_or_404(name)
    all_config = load_plugins_config()
    existing = all_config.get(name, {})
    # Merge: preserve enabled flag and unset keys, apply new values
    merged = {**existing, **payload.config}
    all_config[name] = merged
    save_plugins_config(all_config)
    logger.info("Plugin config updated: %s", name)
    return _build_response(plugin, all_config)
