"""
PermissionService — Phase 6.5

Centralised permission evaluation.  Resolves effective permissions by
combining:
  1. Global role permissions (with role inheritance from ROLE_INHERITANCE)
  2. Object-level ContentPermission rows for a specific content item

Grant/deny precedence for object-level overrides:
  - Explicit deny (granted=False) beats the global role grant.
  - Explicit grant (granted=True) beats the global role deny.
  - If no object-level row exists for the user/role + permission, fall
    back to the global role result.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_permission import ContentPermission
from app.models.user import Role, User
from app.permissions_config.permissions import ALL_PERMISSIONS, get_role_permissions

logger = logging.getLogger(__name__)


class PermissionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Core check ────────────────────────────────────────────────────────────

    async def check_permission(
        self,
        user: User,
        permission: str,
        content_id: int | None = None,
    ) -> bool:
        """
        Return True if *user* is allowed *permission* (optionally scoped to
        *content_id*).

        Steps:
        1. Wildcard roles (admin, superadmin) always pass.
        2. Resolve inherited global permissions.
        3. If content_id supplied, look for object-level overrides.
        """
        role_name: str = user.role.name if user.role else "user"

        # 1. Wildcard → always allowed
        global_perms = get_role_permissions(role_name)
        if "*" in global_perms:
            return True

        # 2. Global role check (with inheritance already resolved)
        globally_allowed = permission in global_perms

        # 3. Object-level override
        if content_id is not None:
            override = await self._get_object_level_decision(
                content_id=content_id,
                user_id=user.id,
                role_name=role_name,
                permission=permission,
            )
            if override is not None:
                return override  # explicit grant or deny wins

        return globally_allowed

    async def get_effective_permissions(
        self,
        user: User,
        content_id: int | None = None,
    ) -> list[str]:
        """
        Return the full list of permission tokens the user has.

        For wildcard roles, returns ALL_PERMISSIONS.
        For content-scoped checks, object-level grants/denies are applied.
        """
        role_name: str = user.role.name if user.role else "user"
        global_perms = get_role_permissions(role_name)

        if "*" in global_perms:
            return sorted(ALL_PERMISSIONS)

        effective: set[str] = set(global_perms)

        if content_id is not None:
            # Apply all object-level rows for this content + user/role
            rows = await self._fetch_object_permissions(
                content_id=content_id,
                user_id=user.id,
                role_name=role_name,
            )
            for row in rows:
                if row.granted:
                    effective.add(row.permission)
                else:
                    effective.discard(row.permission)

        return sorted(effective)

    # ── Object-level permission management ───────────────────────────────────

    async def set_object_permission(
        self,
        content_id: int,
        permission: str,
        granted: bool,
        created_by_id: int,
        *,
        user_id: int | None = None,
        role_name: str | None = None,
    ) -> ContentPermission:
        """
        Create or update an object-level permission override.

        Exactly one of *user_id* or *role_name* must be provided.
        """
        if not (user_id or role_name):
            raise ValueError("Either user_id or role_name must be provided.")
        if user_id and role_name:
            raise ValueError("Provide user_id OR role_name, not both.")
        if permission not in ALL_PERMISSIONS:
            raise ValueError(f"Unknown permission: {permission!r}")

        # Upsert — replace any existing row for same (content, user/role, permission)
        existing = await self._find_existing(content_id, user_id, role_name, permission)
        if existing:
            existing.granted = granted
            existing.created_by_id = created_by_id
            existing.created_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        row = ContentPermission(
            content_id=content_id,
            user_id=user_id,
            role_name=role_name,
            permission=permission,
            granted=granted,
            created_by_id=created_by_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        logger.info(
            "Object permission set: content=%s user=%s role=%s perm=%s granted=%s",
            content_id,
            user_id,
            role_name,
            permission,
            granted,
        )
        return row

    async def list_object_permissions(self, content_id: int) -> list[dict]:
        """List all object-level permission rows for *content_id*."""
        result = await self.db.execute(select(ContentPermission).where(ContentPermission.content_id == content_id))
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "content_id": r.content_id,
                "user_id": r.user_id,
                "role_name": r.role_name,
                "permission": r.permission,
                "granted": r.granted,
                "created_by_id": r.created_by_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def revoke_object_permission(self, permission_id: int) -> None:
        """Delete an object-level permission row by its primary key."""
        row = await self.db.get(ContentPermission, permission_id)
        if row is None:
            raise ValueError(f"ContentPermission {permission_id} not found")
        await self.db.delete(row)
        await self.db.commit()
        logger.info("Object permission revoked: id=%s", permission_id)

    # ── Role permissions (DB-backed) ─────────────────────────────────────────

    async def update_role_permissions(
        self,
        role_name: str,
        permissions: list[str],
    ) -> dict:
        """
        Persist *permissions* to the Role.permissions JSON column in the DB.

        Does NOT change the in-memory ROLE_OWN_PERMISSIONS dict (that is
        source-code; the DB column is the runtime authoritative source).
        """
        result = await self.db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if role is None:
            raise ValueError(f"Role {role_name!r} not found in database")

        # Validate permission tokens (allow "*" for admin/superadmin)
        for p in permissions:
            if p != "*" and p not in ALL_PERMISSIONS:
                raise ValueError(f"Unknown permission token: {p!r}")

        role.permissions = permissions
        await self.db.commit()
        await self.db.refresh(role)
        return {"role": role_name, "permissions": role.permissions}

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _get_object_level_decision(
        self,
        content_id: int,
        user_id: int,
        role_name: str,
        permission: str,
    ) -> bool | None:
        """
        Return the object-level decision (True/False) or None if no row found.

        User-specific rows take precedence over role-based rows.
        """
        # User-specific check first
        result = await self.db.execute(
            select(ContentPermission).where(
                ContentPermission.content_id == content_id,
                ContentPermission.user_id == user_id,
                ContentPermission.permission == permission,
            )
        )
        user_row = result.scalar_one_or_none()
        if user_row is not None:
            return user_row.granted

        # Role-based check
        result = await self.db.execute(
            select(ContentPermission).where(
                ContentPermission.content_id == content_id,
                ContentPermission.role_name == role_name,
                ContentPermission.permission == permission,
                ContentPermission.user_id.is_(None),
            )
        )
        role_row = result.scalar_one_or_none()
        if role_row is not None:
            return role_row.granted

        return None  # no override

    async def _fetch_object_permissions(
        self,
        content_id: int,
        user_id: int,
        role_name: str,
    ) -> list[ContentPermission]:
        """Fetch all object-level rows for this user (by id or role) + content."""
        result = await self.db.execute(
            select(ContentPermission).where(
                ContentPermission.content_id == content_id,
                (ContentPermission.user_id == user_id)
                | ((ContentPermission.role_name == role_name) & ContentPermission.user_id.is_(None)),
            )
        )
        return list(result.scalars().all())

    async def _find_existing(
        self,
        content_id: int,
        user_id: int | None,
        role_name: str | None,
        permission: str,
    ) -> ContentPermission | None:
        """Find an existing row for upsert logic."""
        query = select(ContentPermission).where(
            ContentPermission.content_id == content_id,
            ContentPermission.permission == permission,
        )
        if user_id is not None:
            query = query.where(ContentPermission.user_id == user_id)
        else:
            query = query.where(
                ContentPermission.role_name == role_name,
                ContentPermission.user_id.is_(None),
            )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
