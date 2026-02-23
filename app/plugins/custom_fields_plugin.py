"""
Custom Fields Plugin — Phase 6.2

Adapter wrapping the existing Content Template / Custom Fields functionality:
  - app/models/content_template.py     (ContentTemplate, TemplateField, TemplateRevision)
  - app/routes/templates.py            (template CRUD endpoints)
  - app/services/template_service.py   (TemplateService)

This plugin extends content schema rather than subscribing to event hooks.
It has no hook subscriptions — its value is declarative: advertising to the
admin that custom field types are available.
"""

from __future__ import annotations

import logging
from typing import Any

from app.plugins.base import PluginBase, PluginMeta

logger = logging.getLogger(__name__)

_META = PluginMeta(
    name="custom_fields",
    version="1.0.0",
    description=(
        "Custom field types — 15 field types (text, textarea, richtext, number, date, "
        "datetime, boolean, select, multiselect, image, file, url, email, json, reference) "
        "via content templates with versioning and revision history"
    ),
    hooks=[],  # No event hooks — extends content schema, not the event bus
    config_schema={
        "max_fields_per_template": {"type": "integer", "default": 50},
        "enable_json_field": {"type": "boolean", "default": True},
    },
)


class CustomFieldsPlugin(PluginBase):
    """Custom fields plugin adapter — wraps existing content template system."""

    @property
    def meta(self) -> PluginMeta:
        return _META

    async def on_load(self, config: dict[str, Any]) -> None:
        self._config = config
        logger.debug(
            "CustomFieldsPlugin loaded (max_fields_per_template=%s)",
            config.get("max_fields_per_template", 50),
        )
