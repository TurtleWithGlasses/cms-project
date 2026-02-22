"""
Security Audit Routes — Phase 5.5

GET /api/v1/security/audit   → admin/superadmin only; full security posture report
GET /api/v1/security/headers → public; current security header config + OWASP recommendations
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import require_role
from app.config import settings
from app.models.user import User

router = APIRouter(tags=["Security"])

logger = logging.getLogger(__name__)


class SecurityAuditResponse(BaseModel):
    """Full security posture report."""

    version: str
    environment: str
    score: int
    findings: list[dict[str, str]]
    checked_at: str
    security_features: dict[str, Any]


class HeadersAuditResponse(BaseModel):
    """Security headers configuration and OWASP recommendations."""

    configured_headers: dict[str, str]
    recommendations: list[dict[str, str]]


@router.get("/audit", response_model=SecurityAuditResponse)
async def get_security_audit(
    current_user: User = Depends(require_role(["admin", "superadmin"])),
) -> SecurityAuditResponse:
    """
    Full security posture check (admin/superadmin only).

    Returns a score, per-check findings, and a status map of security features.
    Safe to call repeatedly — all checks are read-only and non-destructive.
    """
    from app.utils.secrets_validator import get_security_posture

    posture = get_security_posture(settings)

    security_features: dict[str, Any] = {
        "hsts_enabled": not settings.debug,
        "debug_disabled": not settings.debug,
        "sentry_configured": bool(settings.sentry_dsn),
        "otel_configured": bool(settings.otel_exporter_endpoint),
        "rate_limiting": True,  # Always on — slowapi wired in main.py
        "csrf_protection": True,  # Always on — CSRFMiddleware in main.py
        "security_headers": True,  # Always on — SecurityHeadersMiddleware in main.py
        "rbac_enabled": True,  # Always on — RBACMiddleware in main.py
        "audit_log_retention_days": settings.audit_log_retention_days,
        "privacy_policy_version": settings.privacy_policy_version,
    }

    return SecurityAuditResponse(
        version=settings.app_version,
        environment=settings.environment,
        score=posture["score"],
        findings=posture["findings"],
        checked_at=posture["checked_at"],
        security_features=security_features,
    )


@router.get("/headers", response_model=HeadersAuditResponse)
async def get_security_headers_audit() -> HeadersAuditResponse:
    """
    Return the current security header configuration and OWASP recommendations.

    Public endpoint — no auth required.
    Useful for automated auditors, penetration testers, and monitoring tools.
    """
    configured_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "geolocation=(), microphone=(), camera=(), payment=(), "
            "usb=(), magnetometer=(), gyroscope=(), accelerometer=()"
        ),
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains (production only)",
    }

    recommendations = [
        {
            "header": "Content-Security-Policy",
            "status": "configured",
            "note": (
                "unsafe-inline and unsafe-eval are present for Tailwind CDN compatibility. "
                "Consider migrating to a self-hosted asset bundle to tighten CSP."
            ),
        },
        {
            "header": "Strict-Transport-Security",
            "status": "production_only",
            "note": "HSTS is disabled in debug/dev mode; enabled automatically in production.",
        },
        {
            "header": "X-Frame-Options",
            "status": "configured",
            "note": "Set to DENY — prevents all framing. Relax to SAMEORIGIN if you embed iframes.",
        },
        {
            "header": "Cross-Origin-Opener-Policy",
            "status": "not_configured",
            "note": "Consider adding COOP: same-origin for additional XS-Leak protection.",
        },
        {
            "header": "Cross-Origin-Resource-Policy",
            "status": "not_configured",
            "note": "Consider CORP: same-origin for API responses to prevent cross-origin reads.",
        },
        {
            "header": "Cross-Origin-Embedder-Policy",
            "status": "not_configured",
            "note": "Required for SharedArrayBuffer access; low priority unless using WebAssembly.",
        },
    ]

    return HeadersAuditResponse(
        configured_headers=configured_headers,
        recommendations=recommendations,
    )
