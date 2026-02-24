"""
Locale helpers — Phase 6.3

Pure functions for BCP 47 locale handling:
- RTL (right-to-left) language detection
- Accept-Language header parsing with quality-value (q=) support
- Language metadata lookup
"""

from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────

# BCP 47 base language codes whose scripts read right-to-left
RTL_LOCALES: frozenset[str] = frozenset({"ar", "he", "fa", "ur", "yi", "ku"})

# Human-readable names for supported locales (subset of BCP 47 code space)
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "ar": "العربية",
    "zh": "中文",
    "ja": "日本語",
    "pt": "Português",
    "it": "Italiano",
    "nl": "Nederlands",
}


# ── Public helpers ────────────────────────────────────────────────────────────


def is_rtl_locale(locale: str) -> bool:
    """Return True when the given BCP 47 locale is right-to-left.

    Compares only the base language tag (before the first hyphen), so
    both "ar" and "ar-SA" are correctly identified as RTL.

    Args:
        locale: BCP 47 locale string, e.g. "ar", "fr-CA", "zh-Hant".

    Returns:
        True if the base language is in RTL_LOCALES, False otherwise.
    """
    base = locale.split("-")[0].lower()
    return base in RTL_LOCALES


def parse_accept_language(header: str, supported: list[str]) -> str | None:
    """Parse an Accept-Language header and return the best matching locale.

    Algorithm:
    1. Split header into tags with optional q-values (default q=1.0).
    2. Sort by q-value descending.
    3. For each tag, try exact match in `supported`, then base-language match.
    4. Return the first match or None if nothing matches.

    Args:
        header:    Value of the Accept-Language HTTP header, e.g.
                   "fr-CA,fr;q=0.9,en-US;q=0.8,en;q=0.7".
        supported: Ordered list of BCP 47 locale codes the server supports.

    Returns:
        The best matching locale from `supported`, or None.
    """
    if not header:
        return None

    # Parse "tag;q=value" pairs
    weighted: list[tuple[float, str]] = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        if ";q=" in part:
            tag, q_str = part.split(";q=", 1)
            try:
                q = float(q_str.strip())
            except ValueError:
                q = 1.0
        else:
            tag = part
            q = 1.0
        weighted.append((q, tag.strip()))

    # Sort by quality value descending (stable sort preserves original order at same q)
    weighted.sort(key=lambda x: x[0], reverse=True)

    supported_lower = [s.lower() for s in supported]

    for _, tag in weighted:
        tag_lower = tag.lower()
        # Exact match
        if tag_lower in supported_lower:
            return supported[supported_lower.index(tag_lower)]
        # Base language match: "fr-CA" → try "fr"
        base = tag_lower.split("-")[0]
        if base in supported_lower:
            return supported[supported_lower.index(base)]

    return None


def get_language_info(locale: str) -> dict[str, str | bool]:
    """Return a metadata dict describing the given locale.

    Args:
        locale: BCP 47 locale code, e.g. "ar", "fr".

    Returns:
        Dict with keys: ``code`` (str), ``name`` (str), ``is_rtl`` (bool).
    """
    return {
        "code": locale,
        "name": LANGUAGE_NAMES.get(locale, locale),
        "is_rtl": is_rtl_locale(locale),
    }
