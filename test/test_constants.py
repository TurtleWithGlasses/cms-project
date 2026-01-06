"""
Tests for constants modules

Tests authentication constants and role-related utility functions.
"""

from unittest.mock import patch

import pytest

from app.constants.auth import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM
from app.constants.roles import (
    ROLE_HIERARCHY,
    get_default_role_name,
    is_higher_role,
)


class TestAuthConstants:
    """Test authentication constants"""

    def test_algorithm_is_set(self):
        """Test that ALGORITHM constant is defined"""
        assert ALGORITHM is not None
        assert isinstance(ALGORITHM, str)
        assert ALGORITHM == "HS256"

    def test_access_token_expire_minutes_is_set(self):
        """Test that ACCESS_TOKEN_EXPIRE_MINUTES is defined"""
        assert ACCESS_TOKEN_EXPIRE_MINUTES is not None
        assert isinstance(ACCESS_TOKEN_EXPIRE_MINUTES, int)
        assert ACCESS_TOKEN_EXPIRE_MINUTES > 0

    @patch.dict("os.environ", {"SECRET_KEY": "your_secret_key"}, clear=True)
    def test_default_secret_key_warning(self, caplog):
        """Test that using default SECRET_KEY triggers a warning"""
        # Force reimport to trigger the warning
        import importlib

        from app.constants import auth

        importlib.reload(auth)

        # Check that warning was logged
        assert any(
            "Using default SECRET_KEY" in record.message and "insecure" in record.message.lower()
            for record in caplog.records
        )


class TestRoleConstants:
    """Test role-related constants"""

    def test_role_hierarchy_exists(self):
        """Test that ROLE_HIERARCHY is defined"""
        assert ROLE_HIERARCHY is not None
        assert isinstance(ROLE_HIERARCHY, dict)
        assert len(ROLE_HIERARCHY) > 0

    def test_role_hierarchy_has_expected_roles(self):
        """Test that ROLE_HIERARCHY contains expected roles"""
        from app.constants.roles import RoleName

        expected_roles = [RoleName.USER, RoleName.EDITOR, RoleName.ADMIN, RoleName.SUPERADMIN]
        for role in expected_roles:
            assert role in ROLE_HIERARCHY

    def test_role_hierarchy_values_are_integers(self):
        """Test that all hierarchy values are integers"""
        for _role, level in ROLE_HIERARCHY.items():
            assert isinstance(level, int)
            assert level >= 0

    def test_superadmin_is_highest_role(self):
        """Test that superadmin has the highest hierarchy value"""
        from app.constants.roles import RoleName

        superadmin_level = ROLE_HIERARCHY.get(RoleName.SUPERADMIN)
        assert superadmin_level is not None

        for role, level in ROLE_HIERARCHY.items():
            if role != RoleName.SUPERADMIN:
                assert level < superadmin_level


class TestGetDefaultRoleName:
    """Test get_default_role_name function"""

    def test_get_default_role_name_returns_string(self):
        """Test that function returns a string"""
        result = get_default_role_name()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_default_role_name_returns_user(self):
        """Test that default role is 'user'"""
        result = get_default_role_name()
        assert result == "user"

    def test_get_default_role_exists_in_hierarchy(self):
        """Test that default role exists in hierarchy"""
        default_role = get_default_role_name()
        assert default_role in ROLE_HIERARCHY


class TestIsHigherRole:
    """Test is_higher_role function"""

    def test_admin_is_higher_than_editor(self):
        """Test that admin is higher than editor"""
        assert is_higher_role("admin", "editor") is True

    def test_admin_is_higher_than_user(self):
        """Test that admin is higher than user"""
        assert is_higher_role("admin", "user") is True

    def test_editor_is_higher_than_user(self):
        """Test that editor is higher than user"""
        assert is_higher_role("editor", "user") is True

    def test_user_is_not_higher_than_editor(self):
        """Test that user is not higher than editor"""
        assert is_higher_role("user", "editor") is False

    def test_user_is_not_higher_than_admin(self):
        """Test that user is not higher than admin"""
        assert is_higher_role("user", "admin") is False

    def test_editor_is_not_higher_than_admin(self):
        """Test that editor is not higher than admin"""
        assert is_higher_role("editor", "admin") is False

    def test_same_role_is_not_higher(self):
        """Test that same role is not considered higher"""
        assert is_higher_role("user", "user") is False
        assert is_higher_role("editor", "editor") is False
        assert is_higher_role("admin", "admin") is False

    def test_superadmin_is_highest(self):
        """Test that superadmin is higher than all other roles"""
        roles = ["user", "editor", "admin"]
        for role in roles:
            assert is_higher_role("superadmin", role) is True

    def test_no_role_is_higher_than_superadmin(self):
        """Test that no role is higher than superadmin"""
        roles = ["user", "editor", "admin"]
        for role in roles:
            assert is_higher_role(role, "superadmin") is False

    def test_unknown_role_defaults_to_zero(self):
        """Test that unknown roles default to hierarchy level 0"""
        # Unknown role vs known role
        assert is_higher_role("unknown_role", "admin") is False
        assert is_higher_role("admin", "unknown_role") is True

        # Two unknown roles
        assert is_higher_role("unknown1", "unknown2") is False

    def test_nonexistent_role_comparison(self):
        """Test comparison with nonexistent roles"""
        # This tests the default value in the .get() call (line 50)
        result = is_higher_role("fake_role", "another_fake_role")
        assert result is False


class TestRoleHierarchyConsistency:
    """Test role hierarchy consistency"""

    def test_hierarchy_is_strictly_ordered(self):
        """Test that hierarchy levels are strictly ordered"""
        roles = ["user", "editor", "manager", "admin", "superadmin"]
        levels = [ROLE_HIERARCHY[role] for role in roles]

        # Check that levels are strictly increasing
        for i in range(len(levels) - 1):
            assert levels[i] < levels[i + 1]

    def test_is_higher_role_is_transitive(self):
        """Test that hierarchy is transitive"""
        # If A > B and B > C, then A > C
        if is_higher_role("admin", "editor") and is_higher_role("editor", "user"):
            assert is_higher_role("admin", "user") is True

    def test_is_higher_role_is_antisymmetric(self):
        """Test that hierarchy is antisymmetric"""
        # If A > B, then B is not > A
        roles = ["user", "editor", "manager", "admin", "superadmin"]
        for i, role1 in enumerate(roles):
            for role2 in roles[i + 1 :]:
                if is_higher_role(role1, role2):
                    assert is_higher_role(role2, role1) is False
