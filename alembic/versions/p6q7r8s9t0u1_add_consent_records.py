"""add consent_records table

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-02-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "p6q7r8s9t0u1"
down_revision: str | None = "o5p6q7r8s9t0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consent_records",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("policy_version", sa.String(20), nullable=False),
        sa.Column(
            "consented_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column(
            "consent_type",
            sa.String(50),
            nullable=False,
            server_default="privacy_policy",
        ),
    )
    op.create_index(
        "idx_consent_user_type",
        "consent_records",
        ["user_id", "consent_type"],
    )
    op.create_index(
        "idx_consent_user_version",
        "consent_records",
        ["user_id", "policy_version"],
    )


def downgrade() -> None:
    op.drop_index("idx_consent_user_version", table_name="consent_records")
    op.drop_index("idx_consent_user_type", table_name="consent_records")
    op.drop_table("consent_records")
