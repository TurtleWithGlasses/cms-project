"""enhance media system with folders, metadata, and image variants

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-02-08 12:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i0j1k2l3m4n5"
down_revision: Union[str, None] = "h9i0j1k2l3m4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create media_folders table
    op.create_table(
        "media_folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["media_folders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_folders_id"), "media_folders", ["id"], unique=False)
    op.create_index("ix_media_folders_slug", "media_folders", ["slug"], unique=False)
    op.create_index("ix_media_folders_user_id", "media_folders", ["user_id"], unique=False)
    op.create_index("ix_media_folders_parent_id", "media_folders", ["parent_id"], unique=False)

    # Add new columns to media table
    op.add_column("media", sa.Column("alt_text", sa.String(), nullable=True))
    op.add_column("media", sa.Column("title", sa.String(), nullable=True))
    op.add_column("media", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("media", sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("media", sa.Column("sizes", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("media", sa.Column("folder_id", sa.Integer(), nullable=True))
    op.add_column("media", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.create_foreign_key("fk_media_folder_id", "media", "media_folders", ["folder_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_media_folder_id", "media", ["folder_id"], unique=False)


def downgrade() -> None:
    # Remove media columns
    op.drop_index("ix_media_folder_id", table_name="media")
    op.drop_constraint("fk_media_folder_id", "media", type_="foreignkey")
    op.drop_column("media", "updated_at")
    op.drop_column("media", "folder_id")
    op.drop_column("media", "sizes")
    op.drop_column("media", "tags")
    op.drop_column("media", "description")
    op.drop_column("media", "title")
    op.drop_column("media", "alt_text")

    # Drop media_folders table
    op.drop_index("ix_media_folders_parent_id", table_name="media_folders")
    op.drop_index("ix_media_folders_user_id", table_name="media_folders")
    op.drop_index("ix_media_folders_slug", table_name="media_folders")
    op.drop_index(op.f("ix_media_folders_id"), table_name="media_folders")
    op.drop_table("media_folders")
