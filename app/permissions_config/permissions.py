"""
Advanced Permission System — Phase 6.5

Provides:
- ALL_PERMISSIONS: canonical list of every defined permission token
- ROLE_OWN_PERMISSIONS: each role's directly-assigned permissions
- ROLE_INHERITANCE: which roles each role inherits permissions from
- PERMISSION_TEMPLATES: predefined permission bundles for quick role assignment
- get_role_permissions(): resolves effective permissions with full inheritance
- ROLE_PERMISSIONS: backward-compat alias for ROLE_OWN_PERMISSIONS
"""

# ── Canonical permission catalogue ────────────────────────────────────────────

ALL_PERMISSIONS: list[str] = [
    # Content CRUD
    "content.create",
    "content.read",
    "content.update",
    "content.delete",
    "content.publish",
    "content.unpublish",
    "content.archive",
    # Workflow
    "workflow.view",
    "workflow.transition",
    "workflow.approve",
    # Media
    "media.upload",
    "media.delete",
    # User management
    "users.view",
    "users.create",
    "users.update",
    "users.delete",
    # Comments
    "comments.moderate",
    "comments.delete",
    # Analytics
    "analytics.view",
    # Settings
    "settings.view",
    "settings.update",
    # Permission management
    "permissions.manage",
]

# ── Per-role own permissions (before inheritance) ─────────────────────────────

ROLE_OWN_PERMISSIONS: dict[str, list[str]] = {
    "user": [
        "content.read",
        "media.upload",
    ],
    "editor": [
        "content.create",
        "content.update",
        "workflow.view",
        "workflow.transition",
    ],
    "manager": [
        "content.publish",
        "content.unpublish",
        "content.archive",
        "workflow.approve",
        "comments.moderate",
        "analytics.view",
    ],
    "admin": ["*"],
    "superadmin": ["*"],
}

# Backward-compat alias used by existing permission_required() calls
ROLE_PERMISSIONS = ROLE_OWN_PERMISSIONS

# ── Role inheritance chains ───────────────────────────────────────────────────

ROLE_INHERITANCE: dict[str, list[str]] = {
    "user": [],
    "editor": ["user"],
    "manager": ["editor"],
    "admin": [],  # admin has "*" wildcard; no chain needed
    "superadmin": [],  # same
}

# ── Permission templates (predefined bundles) ─────────────────────────────────

PERMISSION_TEMPLATES: dict[str, list[str]] = {
    "content_editor": [
        "content.create",
        "content.read",
        "content.update",
        "workflow.view",
        "workflow.transition",
        "media.upload",
    ],
    "content_reviewer": [
        "content.read",
        "workflow.approve",
        "workflow.view",
    ],
    "content_publisher": [
        "content.read",
        "content.publish",
        "content.unpublish",
        "workflow.approve",
    ],
    "media_manager": [
        "media.upload",
        "media.delete",
        "content.read",
    ],
    "analyst": [
        "analytics.view",
        "content.read",
    ],
}

# ── Permission resolver ───────────────────────────────────────────────────────

_KNOWN_ROLES = set(ROLE_OWN_PERMISSIONS.keys())


def get_role_permissions(role: str) -> list[str]:
    """
    Return the effective permissions for *role*, including inherited ones.

    - Admin and superadmin return ``["*"]`` (full access).
    - Unknown roles raise ``ValueError``.
    - Result is sorted and deduplicated for deterministic comparison in tests.
    """
    if role not in _KNOWN_ROLES:
        raise ValueError(f"Invalid role: {role!r}")

    own = ROLE_OWN_PERMISSIONS[role]
    if "*" in own:
        return ["*"]

    effective: set[str] = set(own)

    # Walk the inheritance chain (breadth-first, cycle-safe)
    visited: set[str] = {role}
    queue: list[str] = list(ROLE_INHERITANCE.get(role, []))
    while queue:
        parent = queue.pop(0)
        if parent in visited:
            continue
        visited.add(parent)
        parent_own = ROLE_OWN_PERMISSIONS.get(parent, [])
        if "*" in parent_own:
            return ["*"]
        effective.update(parent_own)
        queue.extend(ROLE_INHERITANCE.get(parent, []))

    return sorted(effective)
