"""
Plugin Hook Constants — Phase 6.2

Centralised list of hook names that plugins can subscribe to.
Hook names follow the `category.action` convention used by WebhookEvent.
"""

from __future__ import annotations

# ── Content lifecycle ──────────────────────────────────────────────────────────
HOOK_CONTENT_CREATED = "content.created"
HOOK_CONTENT_UPDATED = "content.updated"
HOOK_CONTENT_DELETED = "content.deleted"
HOOK_CONTENT_PUBLISHED = "content.published"
HOOK_CONTENT_UNPUBLISHED = "content.unpublished"

# ── Comment hooks ─────────────────────────────────────────────────────────────
HOOK_COMMENT_CREATED = "comment.created"
HOOK_COMMENT_APPROVED = "comment.approved"
HOOK_COMMENT_DELETED = "comment.deleted"

# ── User hooks ────────────────────────────────────────────────────────────────
HOOK_USER_CREATED = "user.created"
HOOK_USER_UPDATED = "user.updated"
HOOK_USER_DELETED = "user.deleted"

# ── Media hooks ───────────────────────────────────────────────────────────────
HOOK_MEDIA_UPLOADED = "media.uploaded"
HOOK_MEDIA_DELETED = "media.deleted"

# ── Master list ───────────────────────────────────────────────────────────────
ALL_HOOKS: list[str] = [
    HOOK_CONTENT_CREATED,
    HOOK_CONTENT_UPDATED,
    HOOK_CONTENT_DELETED,
    HOOK_CONTENT_PUBLISHED,
    HOOK_CONTENT_UNPUBLISHED,
    HOOK_COMMENT_CREATED,
    HOOK_COMMENT_APPROVED,
    HOOK_COMMENT_DELETED,
    HOOK_USER_CREATED,
    HOOK_USER_UPDATED,
    HOOK_USER_DELETED,
    HOOK_MEDIA_UPLOADED,
    HOOK_MEDIA_DELETED,
]
