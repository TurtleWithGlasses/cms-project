"""add_content_translations

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-02-24

Phase 6.3 — Internationalization (i18n)

Creates the `content_translations` table for storing per-locale translations
of Content records (translation-table pattern).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r8s9t0u1v2w3"
down_revision: str = "q7r8s9t0u1v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_translations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column(
            "content_id",
            sa.Integer,
            sa.ForeignKey("content.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locale", sa.String(10), nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("slug", sa.String, nullable=False),
        sa.Column("meta_title", sa.Text, nullable=True),
        sa.Column("meta_description", sa.Text, nullable=True),
        sa.Column("meta_keywords", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "is_rtl",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "translated_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # Composite unique constraint: one translation per (content, locale)
    op.create_unique_constraint(
        "uq_content_translation_locale",
        "content_translations",
        ["content_id", "locale"],
    )

    # Performance indexes
    op.create_index(
        "idx_ct_content_locale",
        "content_translations",
        ["content_id", "locale"],
    )
    op.create_index(
        "idx_ct_locale_status",
        "content_translations",
        ["locale", "status"],
    )
    op.create_index(
        "idx_ct_slug",
        "content_translations",
        ["locale", "slug"],
    )
    op.create_index(
        "idx_ct_content_id",
        "content_translations",
        ["content_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_ct_content_id", table_name="content_translations")
    op.drop_index("idx_ct_slug", table_name="content_translations")
    op.drop_index("idx_ct_locale_status", table_name="content_translations")
    op.drop_index("idx_ct_content_locale", table_name="content_translations")
    op.drop_table("content_translations")
