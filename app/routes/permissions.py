"""
Permission Management Routes — Phase 6.5

Provides endpoints for:
  - Listing all defined permissions and templates
  - Reading/updating role permissions
  - Managing object-level (per-content) permission overrides
  - Checking/introspecting the current user's effective permissions

Route table (all under /api/v1/permissions prefix):
  GET  /                              — permission catalogue + templates (admin)
  GET  /roles/{role_name}             — effective permissions for a role (admin)
  PUT  /roles/{role_name}             — update role permissions in DB (superadmin)
  GET  /content/{content_id}          — list object-level permissions (admin)
  POST /content/{content_id}          — grant/deny object-level permission (admin)
  DELETE /content/{content_id}/{id}   — revoke object-level permission (admin)
  GET  /check                         — check a permission for current user (auth)
  GET  /me                            — all effective permissions for current user (auth)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.permissions_config.permissions import (
    ALL_PERMISSIONS,
    PERMISSION_TEMPLATES,
    get_role_permissions,
)
from app.services.permission_service import PermissionService

router = APIRouter(tags=["Permissions"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class ObjectPermissionCreate(BaseModel):
    permission: str = Field(..., description="Permission token, e.g. 'content.update'")
    granted: bool = Field(True, description="True = grant, False = explicit deny")
    user_id: int | None = Field(None, description="Target user ID (exclusive with role_name)")
    role_name: str | None = Field(None, description="Target role name (exclusive with user_id)")


class RolePermissionsUpdate(BaseModel):
    permissions: list[str] = Field(..., description="Full list of permission tokens for this role")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _require_admin(user: User) -> None:
    role = user.role.name if user.role else ""
    if role not in ("admin", "superadmin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")


def _require_superadmin(user: User) -> None:
    role = user.role.name if user.role else ""
    if role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin privileges required")


# ── Catalogue & templates ─────────────────────────────────────────────────────


@router.get("/")
async def list_permissions(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Return all defined permission tokens and predefined templates.

    Requires admin role.
    """
    _require_admin(current_user)
    return {
        "permissions": ALL_PERMISSIONS,
        "templates": PERMISSION_TEMPLATES,
    }


# ── Role permission management ────────────────────────────────────────────────


@router.get("/roles/{role_name}")
async def get_role_permissions_endpoint(
    role_name: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Return the effective permissions (including inherited) for *role_name*.

    Requires admin role.
    """
    _require_admin(current_user)
    try:
        perms = get_role_permissions(role_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"role": role_name, "permissions": perms}


@router.put("/roles/{role_name}")
async def update_role_permissions(
    role_name: str,
    data: RolePermissionsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Persist a new permission list for *role_name* to the database.

    Updates the Role.permissions JSON column.  Requires superadmin.
    """
    _require_superadmin(current_user)
    service = PermissionService(db)
    try:
        result = await service.update_role_permissions(role_name, data.permissions)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result


# ── Object-level permissions ──────────────────────────────────────────────────


@router.get("/content/{content_id}")
async def list_content_permissions(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    List all object-level permission overrides for *content_id*.

    Requires admin role.
    """
    _require_admin(current_user)
    service = PermissionService(db)
    return await service.list_object_permissions(content_id)


@router.post("/content/{content_id}", status_code=status.HTTP_201_CREATED)
async def create_content_permission(
    content_id: int,
    data: ObjectPermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create or update an object-level permission override for *content_id*.

    Provide either *user_id* or *role_name* (not both).  Requires admin.
    """
    _require_admin(current_user)
    service = PermissionService(db)
    try:
        row = await service.set_object_permission(
            content_id=content_id,
            permission=data.permission,
            granted=data.granted,
            created_by_id=current_user.id,
            user_id=data.user_id,
            role_name=data.role_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "id": row.id,
        "content_id": row.content_id,
        "user_id": row.user_id,
        "role_name": row.role_name,
        "permission": row.permission,
        "granted": row.granted,
    }


@router.delete("/content/{content_id}/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_content_permission(
    content_id: int,  # kept in path for REST semantics; validated implicitly by FK
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Revoke (delete) an object-level permission override by its ID.

    Requires admin role.
    """
    _require_admin(current_user)
    service = PermissionService(db)
    try:
        await service.revoke_object_permission(permission_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Current-user introspection ────────────────────────────────────────────────


@router.get("/check")
async def check_my_permission(
    permission: str = Query(..., description="Permission token to check"),
    content_id: int | None = Query(None, description="Optional content ID for object-level check"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Check whether the current user has *permission* (optionally scoped to *content_id*).

    Returns ``{"permission": "...", "allowed": true/false}``.
    """
    service = PermissionService(db)
    allowed = await service.check_permission(current_user, permission, content_id)
    return {"permission": permission, "content_id": content_id, "allowed": allowed}


@router.get("/me")
async def get_my_permissions(
    content_id: int | None = Query(None, description="Optional content ID for scoped view"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Return all effective permissions for the current user.

    Optionally scoped to a content item (applies object-level overrides).
    """
    service = PermissionService(db)
    perms = await service.get_effective_permissions(current_user, content_id)
    role_name = current_user.role.name if current_user.role else "unknown"
    return {
        "user_id": current_user.id,
        "role": role_name,
        "content_id": content_id,
        "permissions": perms,
    }
