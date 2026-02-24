"""
Permission Dependencies — Phase 6.5

Provides FastAPI Depends()-compatible callables for permission checking:

  permission_required(permission)
      Global role-only check (backward compat).  No DB hit beyond what
      get_current_user already does.

  object_permission_required(permission)
      Full check: global role permissions + object-level ContentPermission
      overrides.  Reads content_id from the request's path parameters
      (key: "content_id") so no tight coupling to specific route signatures.
"""

from fastapi import Depends, HTTPException, Request, status

from app.auth import get_current_user
from app.database import get_db
from app.permissions_config.permissions import get_role_permissions
from app.services.permission_service import PermissionService


def permission_required(permission: str):
    """
    Dependency factory: require *permission* based on global role only.

    Returns the checker coroutine for use as ``Depends(permission_required("x"))``.
    """

    async def checker(current_user=Depends(get_current_user)):
        role = current_user.role.name if current_user.role else "user"
        allowed = get_role_permissions(role)
        if "*" in allowed or permission in allowed:
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action.",
        )

    return checker


def object_permission_required(permission: str):
    """
    Dependency factory: require *permission* with full object-level resolution.

    Reads ``content_id`` from ``request.path_params`` if present (optional).
    Falls back to global role check when no content_id is available.
    """

    async def checker(
        request: Request,
        current_user=Depends(get_current_user),
        db=Depends(get_db),
    ):
        content_id_raw = request.path_params.get("content_id")
        content_id: int | None = int(content_id_raw) if content_id_raw is not None else None

        service = PermissionService(db)
        allowed = await service.check_permission(current_user, permission, content_id)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' denied.",
            )
        return True

    return checker
