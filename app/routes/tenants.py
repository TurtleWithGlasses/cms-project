"""
Tenant Administration Routes — Phase 6.1 Multi-Tenancy

All routes are restricted to superadmin role.

POST   /api/v1/tenants          → create tenant
GET    /api/v1/tenants          → list tenants
GET    /api/v1/tenants/{slug}   → get tenant by slug
PUT    /api/v1/tenants/{slug}   → update tenant
POST   /api/v1/tenants/{slug}/suspend → suspend tenant
DELETE /api/v1/tenants/{slug}   → soft-delete tenant

Also exposes the `get_current_tenant` FastAPI dependency for
tenant-aware routes across the application.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.tenant_service import (
    create_tenant,
    delete_tenant,
    get_tenant_by_slug,
    list_tenants,
    suspend_tenant,
    update_tenant,
)

router = APIRouter(tags=["Tenants"])
logger = logging.getLogger(__name__)


# ── Pydantic schemas ───────────────────────────────────────────────────────────


class TenantCreate(BaseModel):
    name: str
    slug: str
    domain: str | None = None
    plan: str | None = None


class TenantUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    plan: str | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    domain: str | None
    status: str
    plan: str | None
    created_at: str

    @classmethod
    def from_tenant(cls, tenant: Tenant) -> "TenantResponse":
        return cls(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            status=tenant.status,
            plan=tenant.plan,
            created_at=tenant.created_at.isoformat(),
        )


# ── Dependency ─────────────────────────────────────────────────────────────────


async def get_current_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Tenant | None:
    """
    FastAPI dependency that returns the active Tenant for this request.

    Reads request.state.tenant_id set by TenantMiddleware.
    Returns None when multitenancy is disabled or no tenant was resolved
    (backward-compatible with single-tenant mode).
    """
    tenant_id: Any = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        return None
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalars().first()


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_route(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["superadmin"])),
) -> TenantResponse:
    """Create a new tenant organisation (superadmin only)."""
    tenant = await create_tenant(
        name=payload.name,
        slug=payload.slug,
        created_by_id=int(current_user.id),
        db=db,
        plan=payload.plan,
        domain=payload.domain,
    )
    return TenantResponse.from_tenant(tenant)


@router.get("/", response_model=list[TenantResponse])
async def list_tenants_route(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["superadmin"])),
) -> list[TenantResponse]:
    """List all tenant organisations, paginated (superadmin only)."""
    tenants = await list_tenants(db, skip=skip, limit=limit)
    return [TenantResponse.from_tenant(t) for t in tenants]


@router.get("/{slug}", response_model=TenantResponse)
async def get_tenant_route(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["superadmin"])),
) -> TenantResponse:
    """Get a tenant by slug (superadmin only)."""
    tenant = await get_tenant_by_slug(slug, db)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantResponse.from_tenant(tenant)


@router.put("/{slug}", response_model=TenantResponse)
async def update_tenant_route(
    slug: str,
    payload: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["superadmin"])),
) -> TenantResponse:
    """Update a tenant's mutable fields (superadmin only)."""
    tenant = await get_tenant_by_slug(slug, db)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    updates = {k: v for k, v in payload.model_dump(mode="json").items() if v is not None}
    updated = await update_tenant(int(tenant.id), updates, db)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantResponse.from_tenant(updated)


@router.post("/{slug}/suspend", response_model=TenantResponse)
async def suspend_tenant_route(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["superadmin"])),
) -> TenantResponse:
    """Suspend a tenant, blocking all subdomain/header resolution (superadmin only)."""
    tenant = await get_tenant_by_slug(slug, db)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    suspended = await suspend_tenant(int(tenant.id), db)
    if suspended is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantResponse.from_tenant(suspended)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_route(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(["superadmin"])),
) -> None:
    """Soft-delete a tenant (sets status=deleted). Superadmin only."""
    tenant = await get_tenant_by_slug(slug, db)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    deleted = await delete_tenant(int(tenant.id), db)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
