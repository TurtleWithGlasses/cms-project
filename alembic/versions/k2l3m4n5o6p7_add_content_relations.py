"""add content relations, series, and redirects tables

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-02-09 12:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. content_relations table
    op.create_table(
        "content_relations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_content_id",
            sa.Integer(),
            sa.ForeignKey("content.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_content_id",
            sa.Integer(),
            sa.ForeignKey("content.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "relation_type",
            sa.Enum(
                "related_to",
                "part_of_series",
                "depends_on",
                "translated_from",
                name="relationtype",
            ),
            nullable=False,
            server_default="related_to",
        ),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "source_content_id",
            "target_content_id",
            "relation_type",
            name="uq_content_relation",
        ),
    )
    op.create_index("ix_content_relations_id", "content_relations", ["id"])
    op.create_index(
        "ix_content_relations_source",
        "content_relations",
        ["source_content_id", "relation_type"],
    )
    op.create_index(
        "ix_content_relations_target",
        "content_relations",
        ["target_content_id", "relation_type"],
    )

    # 2. content_series table
    op.create_table(
        "content_series",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_content_series_id", "content_series", ["id"])
    op.create_index("ix_content_series_slug", "content_series", ["slug"], unique=True)

    # 3. content_series_items table
    op.create_table(
        "content_series_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "series_id",
            sa.Integer(),
            sa.ForeignKey("content_series.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_id",
            sa.Integer(),
            sa.ForeignKey("content.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("series_id", "content_id", name="uq_series_content"),
    )
    op.create_index("ix_content_series_items_id", "content_series_items", ["id"])
    op.create_index("ix_content_series_items_series", "content_series_items", ["series_id"])
    op.create_index("ix_content_series_items_content", "content_series_items", ["content_id"])
    op.create_index("ix_series_items_order", "content_series_items", ["series_id", "order"])

    # 4. content_redirects table
    op.create_table(
        "content_redirects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("old_slug", sa.String(255), unique=True, nullable=False),
        sa.Column(
            "content_id",
            sa.Integer(),
            sa.ForeignKey("content.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="301"),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_content_redirects_id", "content_redirects", ["id"])
    op.create_index("ix_content_redirects_old_slug", "content_redirects", ["old_slug"], unique=True)
    op.create_index("ix_content_redirects_content", "content_redirects", ["content_id"])


def downgrade() -> None:
    op.drop_table("content_redirects")
    op.drop_table("content_series_items")
    op.drop_table("content_series")
    op.drop_table("content_relations")
    op.execute("DROP TYPE IF EXISTS relationtype")
