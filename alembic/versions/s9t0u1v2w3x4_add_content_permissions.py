"""add_content_permissions

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-02-24

Phase 6.5 — creates the content_permissions table for object-level
permission overrides (grant or deny a specific permission to a user or
role for a specific content item).
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "s9t0u1v2w3x4"
down_revision = "r8s9t0u1v2w3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("role_name", sa.String(length=50), nullable=True),
        sa.Column("permission", sa.String(length=100), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_permissions_id", "content_permissions", ["id"], unique=False)
    op.create_index("ix_content_permissions_content_id", "content_permissions", ["content_id"], unique=False)
    op.create_index("ix_content_permissions_user_id", "content_permissions", ["user_id"], unique=False)
    op.create_index("ix_content_perm_content_user", "content_permissions", ["content_id", "user_id"], unique=False)
    op.create_index("ix_content_perm_content_role", "content_permissions", ["content_id", "role_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_content_perm_content_role", table_name="content_permissions")
    op.drop_index("ix_content_perm_content_user", table_name="content_permissions")
    op.drop_index("ix_content_permissions_user_id", table_name="content_permissions")
    op.drop_index("ix_content_permissions_content_id", table_name="content_permissions")
    op.drop_index("ix_content_permissions_id", table_name="content_permissions")
    op.drop_table("content_permissions")
