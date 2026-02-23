"""
Tenant Resolution Middleware — Phase 6.1 Multi-Tenancy

Resolves the current tenant from:
  1. X-Tenant-Slug request header  (API clients)
  2. Subdomain of the request host (browser clients, e.g. acme.localhost)

Sets request.state.tenant_id and request.state.tenant_slug for downstream
handlers.  When ENABLE_MULTITENANCY is False this middleware is a no-op and
all existing behaviour is unchanged.

Starlette middleware is LIFO — this middleware is registered AFTER
RBACMiddleware in create_app(), so it runs BEFORE RBAC.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request
    from starlette.responses import Response

logger = logging.getLogger(__name__)


def _extract_slug_from_host(host: str, app_domain: str) -> str | None:
    """
    Extract the tenant slug from a subdomain.

    Examples:
        host="acme.localhost", app_domain="localhost" → "acme"
        host="localhost",      app_domain="localhost" → None
        host="a.b.localhost",  app_domain="localhost" → "a.b"
    """
    # Strip port if present
    host = host.split(":")[0]
    if host != app_domain and host.endswith("." + app_domain):
        return host[: -(len(app_domain) + 1)]
    return None


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Resolve the current tenant and attach it to request.state.

    Attributes set on request.state:
        tenant_id   (int | None)  — DB primary key of the active tenant
        tenant_slug (str | None)  — slug string of the active tenant
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Always initialise state so downstream code can safely read without AttributeError
        request.state.tenant_id = None
        request.state.tenant_slug = None

        if not settings.enable_multitenancy:
            return await call_next(request)

        # 1. X-Tenant-Slug header takes priority (explicit API clients)
        slug: str | None = request.headers.get("X-Tenant-Slug")

        # 2. Fall back to subdomain extraction
        if not slug:
            host = request.headers.get("host", "")
            slug = _extract_slug_from_host(host, settings.app_domain)

        if slug:
            # Deferred import avoids circular dependency at module load time
            from app.database import AsyncSessionLocal
            from app.services.tenant_service import get_tenant_by_slug

            async with AsyncSessionLocal() as db:
                tenant = await get_tenant_by_slug(slug, db)

            if tenant and tenant.status == "active":
                request.state.tenant_id = tenant.id
                request.state.tenant_slug = tenant.slug
                logger.debug("TenantMiddleware: resolved tenant_id=%d slug=%s", tenant.id, tenant.slug)

        return await call_next(request)
