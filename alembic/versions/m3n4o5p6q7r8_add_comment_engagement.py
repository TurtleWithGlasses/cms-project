"""add comment engagement tables

Revision ID: m3n4o5p6q7r8
Revises: k2l3m4n5o6p7
Create Date: 2026-02-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m3n4o5p6q7r8"
down_revision: str = "k2l3m4n5o6p7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Comment reactions table
    op.create_table(
        "comment_reactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "reaction_type",
            sa.Enum("like", "dislike", name="reactiontype"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comment_id", "user_id", name="uq_comment_reaction_user"),
    )
    op.create_index(op.f("ix_comment_reactions_id"), "comment_reactions", ["id"])
    op.create_index(op.f("ix_comment_reactions_comment_id"), "comment_reactions", ["comment_id"])
    op.create_index(op.f("ix_comment_reactions_user_id"), "comment_reactions", ["user_id"])

    # Comment reports table
    op.create_table(
        "comment_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum("spam", "harassment", "inappropriate", "other", name="reportreason"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "reviewed", "dismissed", name="reportstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comment_id", "user_id", name="uq_comment_report_user"),
    )
    op.create_index(op.f("ix_comment_reports_id"), "comment_reports", ["id"])
    op.create_index(op.f("ix_comment_reports_comment_id"), "comment_reports", ["comment_id"])
    op.create_index(op.f("ix_comment_reports_user_id"), "comment_reports", ["user_id"])
    op.create_index(op.f("ix_comment_reports_status"), "comment_reports", ["status"])

    # Comment edit history table
    op.create_table(
        "comment_edit_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("previous_body", sa.Text(), nullable=False),
        sa.Column("edited_by", sa.Integer(), nullable=False),
        sa.Column("edited_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["edited_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comment_edit_history_id"), "comment_edit_history", ["id"])
    op.create_index(op.f("ix_comment_edit_history_comment_id"), "comment_edit_history", ["comment_id"])


def downgrade() -> None:
    op.drop_table("comment_edit_history")
    op.drop_table("comment_reports")
    op.drop_table("comment_reactions")

    # Drop enum types
    sa.Enum(name="reactiontype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="reportreason").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="reportstatus").drop(op.get_bind(), checkfirst=True)
