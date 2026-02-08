"""add fulltext search with tsvector, GIN index, trigger, and search_queries table

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-02-08 14:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, None] = "i0j1k2l3m4n5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add search_vector tsvector column to content table
    op.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS search_vector tsvector")

    # 2. Create GIN index for fast full-text search
    op.execute("CREATE INDEX IF NOT EXISTS ix_content_search_vector ON content USING GIN (search_vector)")

    # 3. Create trigger function to auto-update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION content_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.body, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.meta_keywords, '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 4. Create trigger on content table
    op.execute("""
        CREATE TRIGGER content_search_vector_trigger
        BEFORE INSERT OR UPDATE OF title, body, description, meta_keywords
        ON content
        FOR EACH ROW
        EXECUTE FUNCTION content_search_vector_update();
    """)

    # 5. Backfill existing rows
    op.execute("""
        UPDATE content SET search_vector =
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(body, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(meta_keywords, '')), 'D');
    """)

    # 6. Create search_queries table for analytics
    op.create_table(
        "search_queries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("query", sa.String(500), nullable=False),
        sa.Column("normalized_query", sa.String(500), nullable=True),
        sa.Column("results_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("filters_used", sa.JSON(), nullable=True),
        sa.Column("execution_time_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_search_queries_query", "search_queries", ["query"])
    op.create_index(
        "ix_search_queries_normalized_query",
        "search_queries",
        ["normalized_query"],
    )
    op.create_index("ix_search_queries_created_at", "search_queries", ["created_at"])


def downgrade() -> None:
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS content_search_vector_trigger ON content")
    op.execute("DROP FUNCTION IF EXISTS content_search_vector_update()")

    # Drop GIN index
    op.execute("DROP INDEX IF EXISTS ix_content_search_vector")

    # Drop search_vector column
    op.drop_column("content", "search_vector")

    # Drop search_queries table
    op.drop_index("ix_search_queries_created_at", table_name="search_queries")
    op.drop_index("ix_search_queries_normalized_query", table_name="search_queries")
    op.drop_index("ix_search_queries_query", table_name="search_queries")
    op.drop_table("search_queries")
