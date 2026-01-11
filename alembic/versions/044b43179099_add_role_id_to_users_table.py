"""Add role_id to users table

Revision ID: 044b43179099
Revises: e8a87232cd57
Create Date: 2024-11-16 15:22:06.120788

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "044b43179099"
down_revision: Union[str, None] = "e8a87232cd57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create 'roles' table only if it doesn't already exist
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("permissions", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)

    # Check if 'role_id' column already exists in 'users' table
    with op.get_context().autocommit_block():
        conn = op.get_bind()
        result = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='role_id'"
        )
        if not result.fetchone():
            op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=False))
            op.create_foreign_key(None, "users", "roles", ["role_id"], ["id"])

    # Drop 'role' column if it exists
    with op.get_context().autocommit_block():
        conn = op.get_bind()
        result = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='role'"
        )
        if result.fetchone():
            op.drop_column("users", "role")


def downgrade() -> None:
    # Add 'role' column back to 'users' if it was dropped
    with op.get_context().autocommit_block():
        conn = op.get_bind()
        result = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='role'"
        )
        if not result.fetchone():
            op.add_column("users", sa.Column("role", sa.String(length=20), nullable=True))

    # Drop the 'role_id' column and its foreign key
    with op.get_context().autocommit_block():
        conn = op.get_bind()
        result = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='role_id'"
        )
        if result.fetchone():
            op.drop_constraint(None, "users", type_="foreignkey")
            op.drop_column("users", "role_id")

    # Drop the 'roles' table
    op.drop_index(op.f("ix_roles_id"), table_name="roles")
    op.drop_table("roles")
