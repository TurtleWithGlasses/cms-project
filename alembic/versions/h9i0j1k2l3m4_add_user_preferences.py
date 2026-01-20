"""add user preferences column

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-01-20 12:45:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "h9i0j1k2l3m4"
down_revision = "g8h9i0j1k2l3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add preferences column to users table (only if it doesn't exist)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='users' AND column_name='preferences') THEN
                ALTER TABLE users ADD COLUMN preferences JSON;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Remove preferences column from users table (only if it exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name='users' AND column_name='preferences') THEN
                ALTER TABLE users DROP COLUMN preferences;
            END IF;
        END $$;
    """)
