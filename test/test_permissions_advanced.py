"""
Tests for Phase 6.5 Advanced Permissions — granular permissions, role
inheritance, permission templates, object-level overrides, and routes.

All tests run without a live database or Redis connection.

Test classes:
    TestPermissionDefinitions    — ALL_PERMISSIONS catalogue + template validity
    TestRoleInheritance          — get_role_permissions() with inheritance
    TestPermissionTemplates      — PERMISSION_TEMPLATES validity
    TestPermissionServiceLogic   — PermissionService.check_permission() logic (mocked DB)
    TestContentPermissionModel   — ContentPermission model structure
    TestPermissionRoutes         — route registration + auth requirements
    TestPermissionDependency     — dependency factories
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.permissions_config.permissions import (
    ALL_PERMISSIONS,
    PERMISSION_TEMPLATES,
    ROLE_INHERITANCE,
    ROLE_OWN_PERMISSIONS,
    get_role_permissions,
)
from app.services.permission_service import PermissionService
from main import app

# ── TestPermissionDefinitions ─────────────────────────────────────────────────


class TestPermissionDefinitions:
    """ALL_PERMISSIONS catalogue is well-formed."""

    def test_all_permissions_is_list(self):
        assert isinstance(ALL_PERMISSIONS, list)

    def test_all_permissions_non_empty(self):
        assert len(ALL_PERMISSIONS) > 0

    def test_all_permissions_are_strings(self):
        assert all(isinstance(p, str) for p in ALL_PERMISSIONS)

    def test_all_permissions_use_dot_notation(self):
        assert all("." in p for p in ALL_PERMISSIONS)

    def test_no_duplicate_permissions(self):
        assert len(ALL_PERMISSIONS) == len(set(ALL_PERMISSIONS))

    def test_known_permissions_present(self):
        for perm in [
            "content.create",
            "content.publish",
            "workflow.approve",
            "media.upload",
            "users.view",
            "permissions.manage",
        ]:
            assert perm in ALL_PERMISSIONS

    def test_role_own_permissions_keys_are_valid_roles(self):
        known_roles = {"user", "editor", "manager", "admin", "superadmin"}
        assert set(ROLE_OWN_PERMISSIONS.keys()) == known_roles

    def test_role_inheritance_keys_match_role_own_permissions(self):
        assert set(ROLE_INHERITANCE.keys()) == set(ROLE_OWN_PERMISSIONS.keys())


# ── TestRoleInheritance ───────────────────────────────────────────────────────


class TestRoleInheritance:
    """get_role_permissions() resolves inheritance correctly."""

    def test_user_has_content_read(self):
        perms = get_role_permissions("user")
        assert "content.read" in perms

    def test_editor_inherits_user_permissions(self):
        user_perms = get_role_permissions("user")
        editor_perms = get_role_permissions("editor")
        for p in user_perms:
            assert p in editor_perms, f"editor should inherit '{p}' from user"

    def test_editor_has_own_permissions(self):
        perms = get_role_permissions("editor")
        assert "content.create" in perms
        assert "workflow.transition" in perms

    def test_manager_inherits_editor_and_user_permissions(self):
        editor_perms = get_role_permissions("editor")
        manager_perms = get_role_permissions("manager")
        for p in editor_perms:
            assert p in manager_perms, f"manager should inherit '{p}' from editor"

    def test_manager_has_own_permissions(self):
        perms = get_role_permissions("manager")
        assert "workflow.approve" in perms
        assert "content.publish" in perms

    def test_admin_returns_wildcard(self):
        assert get_role_permissions("admin") == ["*"]

    def test_superadmin_returns_wildcard(self):
        assert get_role_permissions("superadmin") == ["*"]

    def test_unknown_role_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid role"):
            get_role_permissions("unknown_role")

    def test_result_is_sorted(self):
        perms = get_role_permissions("manager")
        assert perms == sorted(perms)

    def test_no_duplicates_in_result(self):
        perms = get_role_permissions("manager")
        assert len(perms) == len(set(perms))


# ── TestPermissionTemplates ───────────────────────────────────────────────────


class TestPermissionTemplates:
    """PERMISSION_TEMPLATES are well-formed."""

    def test_templates_is_dict(self):
        assert isinstance(PERMISSION_TEMPLATES, dict)

    def test_templates_non_empty(self):
        assert len(PERMISSION_TEMPLATES) >= 1

    def test_all_template_names_are_strings(self):
        assert all(isinstance(k, str) for k in PERMISSION_TEMPLATES)

    def test_all_template_permissions_in_all_permissions(self):
        for name, perms in PERMISSION_TEMPLATES.items():
            for p in perms:
                assert p in ALL_PERMISSIONS, f"Template '{name}' contains unknown permission: '{p}'"

    def test_each_template_has_at_least_one_permission(self):
        for name, perms in PERMISSION_TEMPLATES.items():
            assert len(perms) >= 1, f"Template '{name}' is empty"

    def test_known_templates_present(self):
        assert "content_editor" in PERMISSION_TEMPLATES
        assert "content_reviewer" in PERMISSION_TEMPLATES
        assert "content_publisher" in PERMISSION_TEMPLATES

    def test_content_editor_template_includes_create(self):
        assert "content.create" in PERMISSION_TEMPLATES["content_editor"]

    def test_analyst_template_includes_analytics_view(self):
        assert "analytics.view" in PERMISSION_TEMPLATES["analyst"]


# ── TestPermissionServiceLogic ────────────────────────────────────────────────


class TestPermissionServiceLogic:
    """PermissionService.check_permission() with mocked DB."""

    def _make_user(self, role_name: str) -> MagicMock:
        user = MagicMock()
        user.id = 1
        user.role = MagicMock()
        user.role.name = role_name
        return user

    def _make_service(self, object_level_result=None) -> PermissionService:
        """Return a PermissionService whose DB calls are stubbed."""
        db = AsyncMock()
        service = PermissionService(db)
        # Stub _get_object_level_decision to return object_level_result
        service._get_object_level_decision = AsyncMock(return_value=object_level_result)
        return service

    @pytest.mark.asyncio
    async def test_admin_always_allowed(self):
        service = self._make_service()
        user = self._make_user("admin")
        assert await service.check_permission(user, "content.delete")

    @pytest.mark.asyncio
    async def test_superadmin_always_allowed(self):
        service = self._make_service()
        user = self._make_user("superadmin")
        assert await service.check_permission(user, "permissions.manage")

    @pytest.mark.asyncio
    async def test_user_allowed_for_content_read(self):
        service = self._make_service()
        user = self._make_user("user")
        assert await service.check_permission(user, "content.read")

    @pytest.mark.asyncio
    async def test_user_denied_for_content_publish(self):
        service = self._make_service()
        user = self._make_user("user")
        assert not await service.check_permission(user, "content.publish")

    @pytest.mark.asyncio
    async def test_editor_inherits_user_permission(self):
        service = self._make_service()
        user = self._make_user("editor")
        assert await service.check_permission(user, "content.read")

    @pytest.mark.asyncio
    async def test_object_level_grant_overrides_global_deny(self):
        # user role cannot publish, but explicit grant for content 5 → allowed
        service = self._make_service(object_level_result=True)
        user = self._make_user("user")
        assert await service.check_permission(user, "content.publish", content_id=5)

    @pytest.mark.asyncio
    async def test_object_level_deny_overrides_global_grant(self):
        # editor can normally create content, but explicit deny for content 7 → denied
        service = self._make_service(object_level_result=False)
        user = self._make_user("editor")
        assert not await service.check_permission(user, "content.create", content_id=7)

    @pytest.mark.asyncio
    async def test_no_object_level_row_falls_back_to_global(self):
        # None = no override; editor can create content globally
        service = self._make_service(object_level_result=None)
        user = self._make_user("editor")
        assert await service.check_permission(user, "content.create", content_id=99)

    @pytest.mark.asyncio
    async def test_get_effective_permissions_admin_returns_all(self):
        service = self._make_service()
        user = self._make_user("admin")
        perms = await service.get_effective_permissions(user)
        assert set(ALL_PERMISSIONS).issubset(set(perms))

    @pytest.mark.asyncio
    async def test_get_effective_permissions_user_subset(self):
        service = self._make_service()
        # Stub _fetch_object_permissions to return empty list
        service._fetch_object_permissions = AsyncMock(return_value=[])
        user = self._make_user("user")
        perms = await service.get_effective_permissions(user)
        assert "content.read" in perms
        assert "content.delete" not in perms

    @pytest.mark.asyncio
    async def test_update_role_permissions_raises_for_unknown_role(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
        service = PermissionService(db)
        with pytest.raises(ValueError, match="not found"):
            await service.update_role_permissions("ghost_role", ["content.read"])

    @pytest.mark.asyncio
    async def test_set_object_permission_raises_if_neither_user_nor_role(self):
        db = AsyncMock()
        service = PermissionService(db)
        with pytest.raises(ValueError, match="user_id or role_name"):
            await service.set_object_permission(1, "content.read", True, 1)


# ── TestContentPermissionModel ────────────────────────────────────────────────


class TestContentPermissionModel:
    """ContentPermission model structure tests (no DB)."""

    def test_model_importable(self):
        from app.models.content_permission import ContentPermission

        assert ContentPermission is not None

    def test_tablename(self):
        from app.models.content_permission import ContentPermission

        assert ContentPermission.__tablename__ == "content_permissions"

    def test_has_content_id_column(self):
        from app.models.content_permission import ContentPermission

        assert "content_id" in ContentPermission.__table__.columns

    def test_has_user_id_column(self):
        from app.models.content_permission import ContentPermission

        assert "user_id" in ContentPermission.__table__.columns

    def test_has_role_name_column(self):
        from app.models.content_permission import ContentPermission

        assert "role_name" in ContentPermission.__table__.columns

    def test_has_permission_column(self):
        from app.models.content_permission import ContentPermission

        assert "permission" in ContentPermission.__table__.columns

    def test_has_granted_column(self):
        from app.models.content_permission import ContentPermission

        assert "granted" in ContentPermission.__table__.columns

    def test_granted_default_is_true(self):
        from app.models.content_permission import ContentPermission

        default = ContentPermission.__table__.columns["granted"].default.arg
        assert default is True

    def test_has_created_at_column(self):
        from app.models.content_permission import ContentPermission

        assert "created_at" in ContentPermission.__table__.columns

    def test_indexes_defined(self):
        from app.models.content_permission import ContentPermission

        index_names = {idx.name for idx in ContentPermission.__table__.indexes}
        assert "ix_content_perm_content_user" in index_names
        assert "ix_content_perm_content_role" in index_names

    def test_repr_method_exists(self):
        from app.models.content_permission import ContentPermission

        assert hasattr(ContentPermission, "__repr__")
        assert callable(ContentPermission.__repr__)


# ── TestPermissionRoutes ──────────────────────────────────────────────────────


class TestPermissionRoutes:
    """Route registration and auth enforcement tests."""

    def test_permissions_root_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/permissions/" in paths

    def test_permissions_roles_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/permissions/roles/{role_name}" in paths

    def test_permissions_content_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/permissions/content/{content_id}" in paths

    def test_permissions_check_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/permissions/check" in paths

    def test_permissions_me_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/permissions/me" in paths

    def test_permissions_revoke_path_registered(self):
        paths = {route.path for route in app.routes}
        assert "/api/v1/permissions/content/{content_id}/{permission_id}" in paths

    def test_router_tag(self):
        from app.routes.permissions import router

        assert "Permissions" in router.tags

    def test_router_importable(self):
        from app.routes.permissions import router

        assert router is not None

    @pytest.mark.asyncio
    async def test_list_permissions_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.get("/api/v1/permissions/")
        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_check_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.get("/api/v1/permissions/check?permission=content.read")
        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_me_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.get("/api/v1/permissions/me")
        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_create_content_permission_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.post(
                "/api/v1/permissions/content/1",
                json={"permission": "content.read", "granted": True, "user_id": 1},
            )
        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_get_role_permissions_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.get("/api/v1/permissions/roles/editor")
        assert response.status_code in (307, 401, 403)


# ── TestPermissionDependency ──────────────────────────────────────────────────


class TestPermissionDependency:
    """Dependency factory callables."""

    def test_permission_required_is_callable(self):
        from app.permissions_config.permission_dependencies import permission_required

        dep = permission_required("content.read")
        assert callable(dep)

    def test_permission_required_returns_coroutine_function(self):
        import inspect

        from app.permissions_config.permission_dependencies import permission_required

        dep = permission_required("content.read")
        assert inspect.iscoroutinefunction(dep)

    def test_object_permission_required_is_callable(self):
        from app.permissions_config.permission_dependencies import object_permission_required

        dep = object_permission_required("content.update")
        assert callable(dep)

    def test_object_permission_required_returns_coroutine_function(self):
        import inspect

        from app.permissions_config.permission_dependencies import object_permission_required

        dep = object_permission_required("content.update")
        assert inspect.iscoroutinefunction(dep)
