"""Add performance indexes

Revision ID: c3d4e5f6g7h8
Revises: b2e3f4a5b6c7
Create Date: 2026-01-17 10:00:00.000000

This migration adds indexes to frequently queried columns
to improve query performance.
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Content table indexes
    op.create_index("ix_content_category_id", "content", ["category_id"], unique=False)
    op.create_index("ix_content_created_at", "content", ["created_at"], unique=False)
    op.create_index("ix_content_updated_at", "content", ["updated_at"], unique=False)
    op.create_index("ix_content_publish_date", "content", ["publish_date"], unique=False)

    # Composite index for common content queries (status + created_at for listing)
    op.create_index(
        "ix_content_status_created",
        "content",
        ["status", "created_at"],
        unique=False,
    )

    # User table indexes
    op.create_index("ix_users_role_id", "users", ["role_id"], unique=False)

    # Media table indexes
    op.create_index("ix_media_uploaded_by", "media", ["uploaded_by"], unique=False)
    op.create_index("ix_media_uploaded_at", "media", ["uploaded_at"], unique=False)

    # Notification table indexes
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_status", "notifications", ["status"], unique=False)
    op.create_index(
        "ix_notifications_user_status",
        "notifications",
        ["user_id", "status"],
        unique=False,
    )

    # Activity logs additional indexes
    op.create_index("ix_activity_logs_timestamp", "activity_logs", ["timestamp"], unique=False)
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"], unique=False)


def downgrade() -> None:
    # Activity logs indexes
    op.drop_index("ix_activity_logs_action", table_name="activity_logs")
    op.drop_index("ix_activity_logs_timestamp", table_name="activity_logs")

    # Notification indexes
    op.drop_index("ix_notifications_user_status", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")

    # Media indexes
    op.drop_index("ix_media_uploaded_at", table_name="media")
    op.drop_index("ix_media_uploaded_by", table_name="media")

    # User indexes
    op.drop_index("ix_users_role_id", table_name="users")

    # Content indexes
    op.drop_index("ix_content_status_created", table_name="content")
    op.drop_index("ix_content_publish_date", table_name="content")
    op.drop_index("ix_content_updated_at", table_name="content")
    op.drop_index("ix_content_created_at", table_name="content")
    op.drop_index("ix_content_category_id", table_name="content")
