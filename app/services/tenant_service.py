"""
Tenant Service — Phase 6.1 Multi-Tenancy

Async CRUD operations for Tenant entities.
All functions accept an injected AsyncSession.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantStatus

logger = logging.getLogger(__name__)


async def create_tenant(
    name: str,
    slug: str,
    created_by_id: int | None,
    db: AsyncSession,
    plan: str | None = None,
    domain: str | None = None,
) -> Tenant:
    """Create a new tenant organisation."""
    tenant = Tenant(
        name=name,
        slug=slug,
        domain=domain,
        plan=plan,
        created_by_id=created_by_id,
        status=TenantStatus.active.value,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    logger.info("Tenant created: id=%d slug=%s", tenant.id, tenant.slug)
    return tenant


async def get_tenant_by_id(tenant_id: int, db: AsyncSession) -> Tenant | None:
    """Return a Tenant by primary key, or None if not found."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalars().first()


async def get_tenant_by_slug(slug: str, db: AsyncSession) -> Tenant | None:
    """Return a Tenant by slug, or None if not found."""
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    return result.scalars().first()


async def get_tenant_by_domain(domain: str, db: AsyncSession) -> Tenant | None:
    """Return a Tenant by custom domain, or None if not found."""
    result = await db.execute(select(Tenant).where(Tenant.domain == domain))
    return result.scalars().first()


async def list_tenants(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
) -> list[Tenant]:
    """Return a paginated list of all tenants (any status)."""
    result = await db.execute(select(Tenant).offset(skip).limit(limit))
    return list(result.scalars().all())


async def update_tenant(
    tenant_id: int,
    updates: dict,
    db: AsyncSession,
) -> Tenant | None:
    """
    Apply a partial update to a Tenant.

    Only keys present in `updates` are changed.
    Returns None if the tenant does not exist.
    """
    tenant = await get_tenant_by_id(tenant_id, db)
    if tenant is None:
        return None
    allowed_fields = {"name", "domain", "plan", "metadata_"}
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def suspend_tenant(tenant_id: int, db: AsyncSession) -> Tenant | None:
    """
    Set a tenant's status to 'suspended'.

    Returns None if the tenant does not exist.
    """
    tenant = await get_tenant_by_id(tenant_id, db)
    if tenant is None:
        return None
    tenant.status = TenantStatus.suspended.value
    await db.commit()
    await db.refresh(tenant)
    logger.info("Tenant suspended: id=%d slug=%s", tenant.id, tenant.slug)
    return tenant


async def delete_tenant(tenant_id: int, db: AsyncSession) -> bool:
    """
    Soft-delete a tenant by setting status to 'deleted'.

    Returns True if the tenant was found and soft-deleted, False otherwise.
    """
    tenant = await get_tenant_by_id(tenant_id, db)
    if tenant is None:
        return False
    tenant.status = TenantStatus.deleted.value
    await db.commit()
    logger.info("Tenant soft-deleted: id=%d slug=%s", tenant.id, tenant.slug)
    return True
