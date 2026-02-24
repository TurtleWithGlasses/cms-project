"""
i18n (Internationalization) package — Phase 6.3

Provides locale helpers, language metadata, RTL detection, and
Accept-Language header parsing for the CMS multi-language content system.
"""

from .locale import (
    LANGUAGE_NAMES,
    RTL_LOCALES,
    get_language_info,
    is_rtl_locale,
    parse_accept_language,
)

__all__ = [
    "LANGUAGE_NAMES",
    "RTL_LOCALES",
    "get_language_info",
    "is_rtl_locale",
    "parse_accept_language",
]
