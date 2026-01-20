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
    # Use raw SQL with IF NOT EXISTS to avoid errors on existing indexes

    # Content table indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_category_id ON content (category_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_created_at ON content (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_updated_at ON content (updated_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_publish_date ON content (publish_date)")

    # Composite index for common content queries (status + created_at for listing)
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_status_created ON content (status, created_at)")

    # User table indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_role_id ON users (role_id)")

    # Media table indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_media_uploaded_by ON media (uploaded_by)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_media_uploaded_at ON media (uploaded_at)")

    # Notification table indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_status ON notifications (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_status ON notifications (user_id, status)")

    # Activity logs additional indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_activity_logs_timestamp ON activity_logs (timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_activity_logs_action ON activity_logs (action)")


def downgrade() -> None:
    # Use raw SQL with IF EXISTS to safely drop indexes

    # Activity logs indexes
    op.execute("DROP INDEX IF EXISTS ix_activity_logs_action")
    op.execute("DROP INDEX IF EXISTS ix_activity_logs_timestamp")

    # Notification indexes
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_status")
    op.execute("DROP INDEX IF EXISTS ix_notifications_status")
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_id")

    # Media indexes
    op.execute("DROP INDEX IF EXISTS ix_media_uploaded_at")
    op.execute("DROP INDEX IF EXISTS ix_media_uploaded_by")

    # User indexes
    op.execute("DROP INDEX IF EXISTS ix_users_role_id")

    # Content indexes
    op.execute("DROP INDEX IF EXISTS ix_content_status_created")
    op.execute("DROP INDEX IF EXISTS ix_content_publish_date")
    op.execute("DROP INDEX IF EXISTS ix_content_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_content_created_at")
    op.execute("DROP INDEX IF EXISTS ix_content_category_id")
