"""
Startup Secrets and Security Posture Validator

Called once at application startup. Non-blocking — logs warnings, never raises.
Provides:
  - validate_secret_key(): check SECRET_KEY quality
  - get_security_posture(): comprehensive per-category security report
"""

import logging
import math
from collections import Counter

logger = logging.getLogger(__name__)

# Known weak or demo secret keys that must never be used in production
_KNOWN_WEAK_KEYS: frozenset[str] = frozenset(
    {
        "secret",
        "secret_key",
        "changeme",
        "your-secret-key",
        "supersecret",
        "development",
        "dev_secret",
        "test_secret",
        "insecure",
        "password",
        "12345678901234567890123456789012",
        "abcdefghijklmnopqrstuvwxyzabcdef",
    }
)

_MIN_KEY_LENGTH = 32
_MIN_ENTROPY = 3.5
_MIN_DISTINCT_CHARS = 8


def _shannon_entropy(key: str) -> float:
    """Compute Shannon entropy (bits per character) of a string."""
    if not key:
        return 0.0
    counts = Counter(key)
    total = len(key)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def validate_secret_key(key: str) -> list[str]:
    """
    Validate SECRET_KEY quality.

    Returns a list of warning strings (empty list = no issues found).
    Never raises — caller decides whether to abort or continue.
    """
    warnings: list[str] = []

    if not key:
        warnings.append("SECRET_KEY is empty — JWT signing is insecure")
        return warnings

    if len(key) < _MIN_KEY_LENGTH:
        warnings.append(f"SECRET_KEY is only {len(key)} chars (minimum {_MIN_KEY_LENGTH} recommended)")

    if key.lower() in _KNOWN_WEAK_KEYS:
        warnings.append("SECRET_KEY matches a known weak/demo value — rotate immediately")

    entropy = _shannon_entropy(key)
    if entropy < _MIN_ENTROPY:
        warnings.append(
            f"SECRET_KEY has low entropy ({entropy:.2f} bits/char) — use a randomly "
            "generated key (e.g. 'openssl rand -hex 32')"
        )

    if len(set(key)) < _MIN_DISTINCT_CHARS:
        warnings.append(
            f"SECRET_KEY uses fewer than {_MIN_DISTINCT_CHARS} distinct characters — entropy is insufficient"
        )

    return warnings


def get_security_posture(settings) -> dict:  # type: ignore[type-arg]
    """
    Perform a comprehensive security posture check.

    Returns:
        {
            "score": int,            # 0–100; higher = better
            "findings": list[dict],  # each: {"severity": "pass|warning|info", "category": str, "message": str}
            "checked_at": str,       # ISO timestamp
        }
    """
    from datetime import datetime, timezone

    findings: list[dict[str, str]] = []

    # --- SECRET_KEY quality ---
    secret_warnings = validate_secret_key(settings.secret_key)
    if secret_warnings:
        for w in secret_warnings:
            findings.append({"severity": "warning", "category": "secrets", "message": w})
    else:
        findings.append(
            {
                "severity": "pass",
                "category": "secrets",
                "message": "SECRET_KEY passes all quality checks",
            }
        )

    # --- DEBUG mode ---
    if settings.debug:
        findings.append(
            {
                "severity": "warning",
                "category": "configuration",
                "message": ("DEBUG=True — SQL logging and full tracebacks are exposed; set DEBUG=False in production"),
            }
        )
    else:
        findings.append(
            {
                "severity": "pass",
                "category": "configuration",
                "message": "DEBUG=False (production safe)",
            }
        )

    # --- Transport / HTTPS ---
    app_url: str = getattr(settings, "app_url", "")
    if settings.environment == "production" and app_url.startswith("http://"):
        findings.append(
            {
                "severity": "warning",
                "category": "transport",
                "message": f"APP_URL uses http:// in production ({app_url}) — HTTPS strongly recommended",
            }
        )
    else:
        findings.append(
            {
                "severity": "pass",
                "category": "transport",
                "message": "APP_URL scheme is acceptable for current environment",
            }
        )

    # --- Database URL (presence check only — never log credentials) ---
    db_url: str = settings.database_url or ""
    if "@" in db_url:
        findings.append(
            {
                "severity": "info",
                "category": "database",
                "message": "DATABASE_URL contains credentials (expected; not logged)",
            }
        )
    else:
        findings.append(
            {
                "severity": "warning",
                "category": "database",
                "message": "DATABASE_URL may be misconfigured (no @ delimiter detected)",
            }
        )

    # --- Data encryption at rest (infrastructure concern) ---
    findings.append(
        {
            "severity": "info",
            "category": "encryption",
            "message": (
                "Data encryption at rest is an infrastructure concern — "
                "verify PostgreSQL disk encryption (LUKS/dm-crypt) or cloud KMS is enabled"
            ),
        }
    )

    # --- Error tracking (Sentry) ---
    if not getattr(settings, "sentry_dsn", None):
        findings.append(
            {
                "severity": "info",
                "category": "monitoring",
                "message": "SENTRY_DSN not set — error tracking disabled",
            }
        )
    else:
        findings.append(
            {
                "severity": "pass",
                "category": "monitoring",
                "message": "Sentry error tracking enabled",
            }
        )

    # --- JWT token expiry ---
    expire_minutes: int = getattr(settings, "access_token_expire_minutes", 30)
    if expire_minutes > 60:
        findings.append(
            {
                "severity": "warning",
                "category": "auth",
                "message": (
                    f"ACCESS_TOKEN_EXPIRE_MINUTES={expire_minutes} — tokens longer than 60 min increase hijacking risk"
                ),
            }
        )
    else:
        findings.append(
            {
                "severity": "pass",
                "category": "auth",
                "message": f"JWT expiry {expire_minutes} min (acceptable)",
            }
        )

    # Score: pass_count / (pass_count + warning_count) * 100
    pass_count = sum(1 for f in findings if f["severity"] == "pass")
    warning_count = sum(1 for f in findings if f["severity"] == "warning")
    total_checks = pass_count + warning_count
    score = int((pass_count / total_checks * 100) if total_checks > 0 else 100)

    return {
        "score": score,
        "findings": findings,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
