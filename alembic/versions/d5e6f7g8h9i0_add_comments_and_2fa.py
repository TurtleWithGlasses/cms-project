"""Add comments and two-factor authentication tables

Revision ID: d5e6f7g8h9i0
Revises: c3d4e5f6g7h8
Create Date: 2026-01-17 12:00:00.000000

This migration adds:
- comments table for content engagement with nested replies
- two_factor_auth table for TOTP-based 2FA
- preferences column to users table
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e6f7g8h9i0"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add preferences column to users table
    op.add_column("users", sa.Column("preferences", sa.JSON(), nullable=True))

    # Create comments table
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "SPAM", name="commentstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("is_edited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("edited_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for comments
    op.create_index("ix_comments_id", "comments", ["id"], unique=False)
    op.create_index("ix_comments_content_id", "comments", ["content_id"], unique=False)
    op.create_index("ix_comments_user_id", "comments", ["user_id"], unique=False)
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"], unique=False)
    op.create_index("ix_comments_status", "comments", ["status"], unique=False)
    op.create_index("ix_comments_content_status", "comments", ["content_id", "status"], unique=False)
    op.create_index("ix_comments_user_created", "comments", ["user_id", "created_at"], unique=False)
    op.create_index("ix_comments_parent_created", "comments", ["parent_id", "created_at"], unique=False)

    # Create two_factor_auth table
    op.create_table(
        "two_factor_auth",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("backup_codes", sa.Text(), nullable=True),
        sa.Column("recovery_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("enabled_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Create indexes for two_factor_auth
    op.create_index("ix_two_factor_auth_id", "two_factor_auth", ["id"], unique=False)
    op.create_index("ix_two_factor_auth_user_id", "two_factor_auth", ["user_id"], unique=True)


def downgrade() -> None:
    # Drop two_factor_auth table and indexes
    op.drop_index("ix_two_factor_auth_user_id", table_name="two_factor_auth")
    op.drop_index("ix_two_factor_auth_id", table_name="two_factor_auth")
    op.drop_table("two_factor_auth")

    # Drop comments table and indexes
    op.drop_index("ix_comments_parent_created", table_name="comments")
    op.drop_index("ix_comments_user_created", table_name="comments")
    op.drop_index("ix_comments_content_status", table_name="comments")
    op.drop_index("ix_comments_status", table_name="comments")
    op.drop_index("ix_comments_parent_id", table_name="comments")
    op.drop_index("ix_comments_user_id", table_name="comments")
    op.drop_index("ix_comments_content_id", table_name="comments")
    op.drop_index("ix_comments_id", table_name="comments")
    op.drop_table("comments")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS commentstatus")

    # Remove preferences column from users
    op.drop_column("users", "preferences")
