"""Add content_tags association table

Revision ID: d595d016aa4f
Revises: 24a4b0390dd8
Create Date: 2024-11-13 20:25:09.402381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd595d016aa4f'
down_revision: Union[str, None] = '24a4b0390dd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
