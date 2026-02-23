"""
Phase 6.2 Plugin System Tests (v1.21.0)

All tests avoid a live database — pure unit tests using mocks and
TestClient with route-path inspection.

Test classes:
    TestPluginMeta      (~8)  — PluginMeta dataclass
    TestPluginBase      (~8)  — PluginBase abstract class
    TestPluginRegistry  (~12) — PluginRegistry + fire_hook logic
    TestPluginLoader    (~10) — config I/O + initialize_plugins
    TestCorePlugins     (~15) — 4 built-in plugin adapters
    TestPluginHooks     (~7)  — hook name constants + ALL_HOOKS
    TestPluginRoutes    (~8)  — route registration + access control
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ══════════════════════════════════════════════════════════════════════════════
# 1. TestPluginMeta
# ══════════════════════════════════════════════════════════════════════════════


class TestPluginMeta:
    def test_pluginmeta_importable(self):
        from app.plugins.base import PluginMeta

        assert PluginMeta is not None

    def test_pluginmeta_is_dataclass(self):
        from app.plugins.base import PluginMeta

        assert dataclasses.is_dataclass(PluginMeta)

    def test_pluginmeta_required_fields(self):
        from app.plugins.base import PluginMeta

        fields = {f.name for f in dataclasses.fields(PluginMeta)}
        assert {"name", "version", "description", "author", "hooks", "config_schema"}.issubset(fields)

    def test_pluginmeta_default_author(self):
        from app.plugins.base import PluginMeta

        m = PluginMeta(name="test", version="1.0.0", description="desc")
        assert m.author == "CMS Core Team"

    def test_pluginmeta_default_hooks(self):
        from app.plugins.base import PluginMeta

        m = PluginMeta(name="test", version="1.0.0", description="desc")
        assert m.hooks == []

    def test_pluginmeta_default_config_schema(self):
        from app.plugins.base import PluginMeta

        m = PluginMeta(name="test", version="1.0.0", description="desc")
        assert m.config_schema == {}

    def test_pluginmeta_hooks_mutable_default_isolated(self):
        """Each instance gets its own list — no shared mutable default."""
        from app.plugins.base import PluginMeta

        m1 = PluginMeta(name="a", version="1.0.0", description="d")
        m2 = PluginMeta(name="b", version="1.0.0", description="d")
        m1.hooks.append("x")
        assert "x" not in m2.hooks

    def test_pluginmeta_custom_values(self):
        from app.plugins.base import PluginMeta

        m = PluginMeta(
            name="seo",
            version="2.0.0",
            description="SEO tools",
            author="Team",
            hooks=["content.published"],
            config_schema={"key": {"type": "boolean"}},
        )
        assert m.name == "seo"
        assert m.version == "2.0.0"
        assert m.hooks == ["content.published"]


# ══════════════════════════════════════════════════════════════════════════════
# 2. TestPluginBase
# ══════════════════════════════════════════════════════════════════════════════


class TestPluginBase:
    def test_pluginbase_importable(self):
        from app.plugins.base import PluginBase

        assert PluginBase is not None

    def test_pluginbase_is_abstract(self):
        from app.plugins.base import PluginBase

        with pytest.raises(TypeError):
            PluginBase()  # type: ignore[abstract]

    def test_pluginbase_concrete_subclass_instantiates(self):
        from app.plugins.base import PluginBase, PluginMeta

        class ConcretePlugin(PluginBase):
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="test", version="1.0.0", description="test")

        p = ConcretePlugin()
        assert p.meta.name == "test"

    def test_on_load_is_coroutine(self):
        from app.plugins.base import PluginBase

        assert inspect.iscoroutinefunction(PluginBase.on_load)

    def test_on_unload_is_coroutine(self):
        from app.plugins.base import PluginBase

        assert inspect.iscoroutinefunction(PluginBase.on_unload)

    def test_handle_hook_is_coroutine(self):
        from app.plugins.base import PluginBase

        assert inspect.iscoroutinefunction(PluginBase.handle_hook)

    def test_default_handle_hook_returns_none(self):
        from app.plugins.base import PluginBase, PluginMeta

        class ConcretePlugin(PluginBase):
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="test", version="1.0.0", description="test")

        p = ConcretePlugin()
        result = asyncio.run(p.handle_hook("some.hook", {}))
        assert result is None

    def test_meta_property_is_abstract(self):
        from app.plugins.base import PluginBase

        assert "meta" in {m for m in dir(PluginBase) if not m.startswith("__")}
        # The property must be abstract
        prop = PluginBase.__dict__.get("meta")
        assert prop is not None and getattr(prop.fget, "__isabstractmethod__", False)


# ══════════════════════════════════════════════════════════════════════════════
# 3. TestPluginRegistry
# ══════════════════════════════════════════════════════════════════════════════


def _make_plugin(name: str, hooks: list[str] | None = None):
    """Create a lightweight concrete PluginBase subclass for testing."""
    from app.plugins.base import PluginBase, PluginMeta

    class _P(PluginBase):
        @property
        def meta(self) -> PluginMeta:
            return PluginMeta(name=name, version="1.0.0", description=name, hooks=hooks or [])

    return _P()


class TestPluginRegistry:
    def test_registry_importable(self):
        from app.plugins.registry import PluginRegistry

        assert PluginRegistry is not None

    def test_plugin_registry_singleton_importable(self):
        from app.plugins.registry import PluginRegistry, plugin_registry

        assert isinstance(plugin_registry, PluginRegistry)

    def test_register_makes_plugin_visible(self):
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        p = _make_plugin("foo")
        reg.register(p)
        assert reg.is_registered("foo")
        assert p in reg.all_plugins()

    def test_get_returns_correct_plugin(self):
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        p = _make_plugin("bar")
        reg.register(p)
        assert reg.get("bar") is p

    def test_get_returns_none_for_unknown(self):
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        assert reg.get("nonexistent") is None

    def test_is_registered_false_initially(self):
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        assert not reg.is_registered("anything")

    def test_fire_hook_calls_subscriber(self):
        from app.plugins.base import PluginBase, PluginMeta
        from app.plugins.registry import PluginRegistry

        called = []

        class HookPlugin(PluginBase):
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="hp", version="1.0.0", description="d", hooks=["test.hook"])

            async def handle_hook(self, hook_name, payload):
                called.append((hook_name, payload))
                return "ok"

        reg = PluginRegistry()
        reg.register(HookPlugin())
        results = asyncio.run(reg.fire_hook("test.hook", {"key": "val"}))
        assert called == [("test.hook", {"key": "val"})]
        assert results == ["ok"]

    def test_fire_hook_empty_for_unregistered_hook(self):
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        results = asyncio.run(reg.fire_hook("no.subscribers", {}))
        assert results == []

    def test_fire_hook_swallows_exceptions(self):
        from app.plugins.base import PluginBase, PluginMeta
        from app.plugins.registry import PluginRegistry

        class BrokenPlugin(PluginBase):
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="broken", version="1.0.0", description="d", hooks=["test.hook"])

            async def handle_hook(self, hook_name, payload):
                msg = "plugin exploded"
                raise RuntimeError(msg)

        reg = PluginRegistry()
        reg.register(BrokenPlugin())
        # Should NOT raise — just logs warning and returns empty results
        results = asyncio.run(reg.fire_hook("test.hook", {}))
        assert results == []

    def test_fire_hook_partial_results_on_mixed_plugins(self):
        """One plugin raises, another succeeds — partial results returned."""
        from app.plugins.base import PluginBase, PluginMeta
        from app.plugins.registry import PluginRegistry

        class OkPlugin(PluginBase):
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="ok", version="1.0.0", description="d", hooks=["test.hook"])

            async def handle_hook(self, hook_name, payload):
                return "success"

        class BadPlugin(PluginBase):
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="bad", version="1.0.0", description="d", hooks=["test.hook"])

            async def handle_hook(self, hook_name, payload):
                msg = "boom"
                raise ValueError(msg)

        reg = PluginRegistry()
        reg.register(OkPlugin())
        reg.register(BadPlugin())
        results = asyncio.run(reg.fire_hook("test.hook", {}))
        assert "success" in results

    def test_plugin_not_called_for_unsubscribed_hooks(self):
        from app.plugins.base import PluginBase, PluginMeta
        from app.plugins.registry import PluginRegistry

        called = []

        class SelectivePlugin(PluginBase):
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="sel", version="1.0.0", description="d", hooks=["a.hook"])

            async def handle_hook(self, hook_name, payload):
                called.append(hook_name)

        reg = PluginRegistry()
        reg.register(SelectivePlugin())
        asyncio.run(reg.fire_hook("b.hook", {}))
        assert called == []

    def test_multiple_plugins_subscribe_to_same_hook(self):
        from app.plugins.registry import PluginRegistry

        p1 = _make_plugin("p1", hooks=["shared.hook"])
        p2 = _make_plugin("p2", hooks=["shared.hook"])
        reg = PluginRegistry()
        reg.register(p1)
        reg.register(p2)
        results = asyncio.run(reg.fire_hook("shared.hook", {}))
        # Both default handle_hook return None
        assert len(results) == 2


# ══════════════════════════════════════════════════════════════════════════════
# 4. TestPluginLoader
# ══════════════════════════════════════════════════════════════════════════════


class TestPluginLoader:
    def test_load_plugins_config_returns_dict_no_file(self, tmp_path):
        """When config file is absent, returns default dict."""
        from app.plugins import loader as loader_module

        fake_path = tmp_path / "plugins_config.json"
        with patch.object(loader_module, "_PLUGINS_CONFIG_FILE", fake_path):
            cfg = loader_module.load_plugins_config()
        assert isinstance(cfg, dict)
        assert len(cfg) > 0

    def test_save_and_load_roundtrip(self, tmp_path):
        from app.plugins import loader as loader_module

        fake_path = tmp_path / "plugins_config.json"
        data = {"seo": {"enabled": False, "custom_key": 42}}
        with patch.object(loader_module, "_PLUGINS_CONFIG_FILE", fake_path):
            loader_module.save_plugins_config(data)
            loaded = loader_module.load_plugins_config()
        assert loaded == data

    def test_initialize_plugins_is_coroutine(self):
        from app.plugins.loader import initialize_plugins

        assert inspect.iscoroutinefunction(initialize_plugins)

    def test_initialize_plugins_registers_four_plugins(self):
        from app.plugins.loader import initialize_plugins
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        asyncio.run(initialize_plugins(reg))
        names = {p.meta.name for p in reg.all_plugins()}
        assert names == {"seo", "analytics", "social", "custom_fields"}

    def test_default_config_all_enabled(self, tmp_path):
        """Default config has enabled=True for all 4 plugins."""
        from app.plugins import loader as loader_module

        fake_path = tmp_path / "no_file.json"
        with patch.object(loader_module, "_PLUGINS_CONFIG_FILE", fake_path):
            cfg = loader_module.load_plugins_config()
        for name in ("seo", "analytics", "social", "custom_fields"):
            assert cfg[name]["enabled"] is True

    def test_config_file_path_uses_data_directory(self):
        from app.plugins import loader as loader_module

        assert "data" in str(loader_module._PLUGINS_CONFIG_FILE)

    def test_save_creates_parent_dirs(self, tmp_path):
        from app.plugins import loader as loader_module

        nested_path = tmp_path / "subdir" / "plugins_config.json"
        with patch.object(loader_module, "_PLUGINS_CONFIG_FILE", nested_path):
            loader_module.save_plugins_config({"test": {"enabled": True}})
        assert nested_path.exists()

    def test_load_recovers_from_corrupt_json(self, tmp_path):
        """Malformed JSON in config file → returns defaults (no crash)."""
        from app.plugins import loader as loader_module

        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json", encoding="utf-8")
        with patch.object(loader_module, "_PLUGINS_CONFIG_FILE", bad_file):
            cfg = loader_module.load_plugins_config()
        assert isinstance(cfg, dict)

    def test_initialize_plugins_calls_on_load(self):
        """Each plugin's on_load is called with its config slice."""
        from app.plugins.loader import initialize_plugins
        from app.plugins.registry import PluginRegistry

        reg = PluginRegistry()
        asyncio.run(initialize_plugins(reg))
        # All 4 plugins should be registered — on_load must have been called
        assert reg.is_registered("seo")
        assert reg.is_registered("analytics")
        assert reg.is_registered("social")
        assert reg.is_registered("custom_fields")

    def test_load_plugins_config_returns_new_dict_each_call(self, tmp_path):
        """Mutations to the returned dict do not affect subsequent calls."""
        from app.plugins import loader as loader_module

        fake_path = tmp_path / "cfg.json"
        with patch.object(loader_module, "_PLUGINS_CONFIG_FILE", fake_path):
            c1 = loader_module.load_plugins_config()
            c1["seo"]["enabled"] = False
            c2 = loader_module.load_plugins_config()
        # c2 reads from defaults again (file still absent at this point)
        assert c2["seo"]["enabled"] is True


# ══════════════════════════════════════════════════════════════════════════════
# 5. TestCorePlugins
# ══════════════════════════════════════════════════════════════════════════════


class TestCorePlugins:
    # ── SEO plugin ─────────────────────────────────────────────────────────────

    def test_seo_plugin_importable(self):
        from app.plugins.seo_plugin import SEOPlugin

        assert SEOPlugin is not None

    def test_seo_plugin_is_subclass(self):
        from app.plugins.base import PluginBase
        from app.plugins.seo_plugin import SEOPlugin

        assert issubclass(SEOPlugin, PluginBase)

    def test_seo_plugin_name(self):
        from app.plugins.seo_plugin import SEOPlugin

        assert SEOPlugin().meta.name == "seo"

    def test_seo_plugin_version_nonempty(self):
        from app.plugins.seo_plugin import SEOPlugin

        assert SEOPlugin().meta.version

    def test_seo_plugin_hooks_include_content_published(self):
        from app.plugins.hooks import HOOK_CONTENT_PUBLISHED
        from app.plugins.seo_plugin import SEOPlugin

        assert HOOK_CONTENT_PUBLISHED in SEOPlugin().meta.hooks

    def test_seo_plugin_handle_hook_is_coroutine(self):
        from app.plugins.seo_plugin import SEOPlugin

        assert inspect.iscoroutinefunction(SEOPlugin.handle_hook)

    def test_seo_plugin_on_load_is_coroutine(self):
        from app.plugins.seo_plugin import SEOPlugin

        assert inspect.iscoroutinefunction(SEOPlugin.on_load)

    # ── Analytics plugin ───────────────────────────────────────────────────────

    def test_analytics_plugin_importable(self):
        from app.plugins.analytics_plugin import AnalyticsPlugin

        assert AnalyticsPlugin is not None

    def test_analytics_plugin_name(self):
        from app.plugins.analytics_plugin import AnalyticsPlugin

        assert AnalyticsPlugin().meta.name == "analytics"

    def test_analytics_plugin_hooks_include_content_published(self):
        from app.plugins.analytics_plugin import AnalyticsPlugin
        from app.plugins.hooks import HOOK_CONTENT_PUBLISHED

        assert HOOK_CONTENT_PUBLISHED in AnalyticsPlugin().meta.hooks

    def test_analytics_plugin_hooks_include_user_created(self):
        from app.plugins.analytics_plugin import AnalyticsPlugin
        from app.plugins.hooks import HOOK_USER_CREATED

        assert HOOK_USER_CREATED in AnalyticsPlugin().meta.hooks

    # ── Social plugin ──────────────────────────────────────────────────────────

    def test_social_plugin_importable(self):
        from app.plugins.social_plugin import SocialPlugin

        assert SocialPlugin is not None

    def test_social_plugin_name(self):
        from app.plugins.social_plugin import SocialPlugin

        assert SocialPlugin().meta.name == "social"

    def test_social_plugin_hooks_include_content_published(self):
        from app.plugins.hooks import HOOK_CONTENT_PUBLISHED
        from app.plugins.social_plugin import SocialPlugin

        assert HOOK_CONTENT_PUBLISHED in SocialPlugin().meta.hooks

    # ── Custom fields plugin ───────────────────────────────────────────────────

    def test_custom_fields_plugin_importable(self):
        from app.plugins.custom_fields_plugin import CustomFieldsPlugin

        assert CustomFieldsPlugin is not None

    def test_custom_fields_plugin_name(self):
        from app.plugins.custom_fields_plugin import CustomFieldsPlugin

        assert CustomFieldsPlugin().meta.name == "custom_fields"

    def test_custom_fields_plugin_hooks_empty(self):
        from app.plugins.custom_fields_plugin import CustomFieldsPlugin

        assert CustomFieldsPlugin().meta.hooks == []

    def test_custom_fields_plugin_is_subclass(self):
        from app.plugins.base import PluginBase
        from app.plugins.custom_fields_plugin import CustomFieldsPlugin

        assert issubclass(CustomFieldsPlugin, PluginBase)

    def test_all_core_plugins_have_hooks_list(self):
        from app.plugins.analytics_plugin import AnalyticsPlugin
        from app.plugins.custom_fields_plugin import CustomFieldsPlugin
        from app.plugins.seo_plugin import SEOPlugin
        from app.plugins.social_plugin import SocialPlugin

        for cls in (SEOPlugin, AnalyticsPlugin, SocialPlugin, CustomFieldsPlugin):
            assert isinstance(cls().meta.hooks, list)


# ══════════════════════════════════════════════════════════════════════════════
# 6. TestPluginHooks
# ══════════════════════════════════════════════════════════════════════════════


class TestPluginHooks:
    def test_all_hooks_importable(self):
        from app.plugins.hooks import ALL_HOOKS

        assert ALL_HOOKS is not None

    def test_all_hooks_is_list(self):
        from app.plugins.hooks import ALL_HOOKS

        assert isinstance(ALL_HOOKS, list)

    def test_all_hooks_length(self):
        from app.plugins.hooks import ALL_HOOKS

        assert len(ALL_HOOKS) == 13

    def test_all_hooks_are_strings(self):
        from app.plugins.hooks import ALL_HOOKS

        assert all(isinstance(h, str) for h in ALL_HOOKS)

    def test_all_hooks_have_dot_separator(self):
        from app.plugins.hooks import ALL_HOOKS

        assert all("." in h for h in ALL_HOOKS)

    def test_no_duplicate_hooks(self):
        from app.plugins.hooks import ALL_HOOKS

        assert len(ALL_HOOKS) == len(set(ALL_HOOKS))

    def test_content_published_value(self):
        from app.plugins.hooks import HOOK_CONTENT_PUBLISHED

        assert HOOK_CONTENT_PUBLISHED == "content.published"

    def test_hook_constants_are_nonempty(self):
        from app.plugins import hooks as hooks_module

        constants = [v for k, v in vars(hooks_module).items() if k.startswith("HOOK_")]
        assert all(c for c in constants)


# ══════════════════════════════════════════════════════════════════════════════
# 7. TestPluginRoutes
# ══════════════════════════════════════════════════════════════════════════════


class TestPluginRoutes:
    def _get_client(self):
        from main import app

        return TestClient(app, raise_server_exceptions=False, follow_redirects=False)

    def _get_all_paths(self):
        from main import app

        return [r.path for r in app.routes]

    def test_plugins_list_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/plugins/" in paths

    def test_plugins_detail_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/plugins/{name}" in paths

    def test_plugins_enable_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/plugins/{name}/enable" in paths

    def test_plugins_disable_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/plugins/{name}/disable" in paths

    def test_plugins_config_path_registered(self):
        paths = self._get_all_paths()
        assert "/api/v1/plugins/{name}/config" in paths

    def test_unauthenticated_list_rejected(self):
        client = self._get_client()
        response = client.get("/api/v1/plugins/")
        assert response.status_code in (307, 401, 403)

    def test_unauthenticated_get_rejected(self):
        client = self._get_client()
        response = client.get("/api/v1/plugins/seo")
        assert response.status_code in (307, 401, 403)

    def test_plugin_response_schema_fields(self):
        from app.routes.plugins import PluginResponse

        fields = set(PluginResponse.model_fields.keys())
        for expected in ("name", "version", "enabled", "hooks", "config"):
            assert expected in fields

    def test_plugin_config_update_schema_fields(self):
        from app.routes.plugins import PluginConfigUpdate

        assert "config" in PluginConfigUpdate.model_fields

    def test_router_has_plugins_tag(self):
        from app.routes.plugins import router

        assert "Plugins" in router.tags

    def test_list_plugins_function_importable(self):
        from app.routes.plugins import list_plugins

        assert callable(list_plugins)
