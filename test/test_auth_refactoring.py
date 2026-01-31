"""
Tests for authentication code refactoring

Verifies that authentication code has been properly consolidated and
hardcoded values removed.
"""

import inspect
from pathlib import Path


class TestAuthServiceRefactoring:
    """Test authentication service improvements"""

    def test_no_hardcoded_role_id(self):
        """Auth service should not have hardcoded role IDs"""
        from app.services import auth_service

        # Read the source code of register_user function
        source = inspect.getsource(auth_service.register_user)

        # Should not contain hardcoded role_id=2 or role_id=3
        assert "role_id=2" not in source
        assert "role_id=3" not in source

        # Should use get_default_role_name
        assert "get_default_role_name" in source

    def test_role_constants_defined(self):
        """Role constants should be properly defined"""
        from app.constants.roles import DEFAULT_ROLE, ROLE_HIERARCHY, RoleName

        # Verify RoleName enum exists with expected values
        assert hasattr(RoleName, "USER")
        assert hasattr(RoleName, "EDITOR")
        assert hasattr(RoleName, "MANAGER")
        assert hasattr(RoleName, "ADMIN")
        assert hasattr(RoleName, "SUPERADMIN")

        # Verify default role is set
        assert DEFAULT_ROLE is not None
        assert DEFAULT_ROLE == RoleName.USER

        # Verify role hierarchy has all roles
        assert len(ROLE_HIERARCHY) >= 5

    def test_auth_module_consolidated(self):
        """Auth module should have all required exports"""
        from app.auth import (
            create_access_token,
            decode_access_token,
            get_current_user,
            has_permission,
            hash_password,
            require_role,
            verify_password,
        )

        # All functions should be callable
        assert callable(hash_password)
        assert callable(verify_password)
        assert callable(create_access_token)
        assert callable(decode_access_token)
        assert callable(get_current_user)
        assert callable(require_role)
        assert callable(has_permission)

    def test_no_redundant_auth_utils(self):
        """There should be no separate auth_utils or auth_helpers files"""
        utils_dir = Path(__file__).parent.parent / "app" / "utils"
        if utils_dir.exists():
            files = [f.name for f in utils_dir.iterdir()]
            auth_files = [f for f in files if "auth" in f.lower()]
            # Should be empty - all auth code consolidated in app/auth.py
            assert auth_files == [], f"Found redundant auth files: {auth_files}"

    def test_get_default_role_name_function(self):
        """get_default_role_name should return the default user role"""
        from app.constants.roles import get_default_role_name

        role_name = get_default_role_name()
        assert role_name == "user"
        assert isinstance(role_name, str)
