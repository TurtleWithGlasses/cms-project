"""add utm columns to content views

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-02-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o5p6q7r8s9t0"
down_revision: str | None = "n4o5p6q7r8s9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UTM_COLUMNS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")


def upgrade() -> None:
    for col in UTM_COLUMNS:
        op.add_column("content_views", sa.Column(col, sa.String(100), nullable=True))


def downgrade() -> None:
    for col in UTM_COLUMNS:
        op.drop_column("content_views", col)
