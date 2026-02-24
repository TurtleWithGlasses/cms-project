"""
Language Detection Middleware — Phase 6.3 Internationalization

Sets request.state.locale from:
  1. X-Language request header (exact match against supported list)
  2. Accept-Language header (quality-weighted, best-match)
  3. settings.default_language (fallback)

No DB lookups — pure header parsing.  Registered in create_app() AFTER
TenantMiddleware (Starlette LIFO → runs before TenantMiddleware and RBAC).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.i18n.locale import parse_accept_language

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request
    from starlette.responses import Response


class LanguageMiddleware(BaseHTTPMiddleware):
    """Detect the request locale and attach it to request.state.locale.

    Detection order:
    1. ``X-Language`` header — must be an exact member of supported_languages.
    2. ``Accept-Language`` header — quality-weighted BCP 47 matching.
    3. ``settings.default_language`` — always a valid fallback.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Explicit header takes priority
        locale = request.headers.get("X-Language", "").strip()
        if locale not in settings.supported_languages:
            # 2. Accept-Language quality matching
            locale = (
                parse_accept_language(
                    request.headers.get("Accept-Language", ""),
                    settings.supported_languages,
                )
                or settings.default_language
            )
        request.state.locale = locale
        return await call_next(request)
