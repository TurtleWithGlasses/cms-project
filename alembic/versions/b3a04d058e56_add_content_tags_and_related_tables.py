"""Add content_tags and related tables

Revision ID: b3a04d058e56
Revises: d595d016aa4f
Create Date: 2024-11-13 20:36:06.520183

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3a04d058e56'
down_revision: Union[str, None] = 'd595d016aa4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_id'), 'tags', ['id'], unique=False)
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=True)
    op.create_table('content',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('slug', sa.String(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('publish_date', sa.DateTime(), nullable=True),
    sa.Column('status', sa.Enum('DRAFT', 'PENDING', 'PUBLISHED', name='contentstatus'), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('meta_title', sa.String(), nullable=True),
    sa.Column('meta_description', sa.Text(), nullable=True),
    sa.Column('meta_keywords', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug', name='unique_slug')
    )
    op.create_index(op.f('ix_content_id'), 'content', ['id'], unique=False)
    op.create_index(op.f('ix_content_slug'), 'content', ['slug'], unique=True)
    op.create_index(op.f('ix_content_title'), 'content', ['title'], unique=False)
    op.create_table('content_tags',
    sa.Column('content_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['content_id'], ['content.id'], ),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
    sa.PrimaryKeyConstraint('content_id', 'tag_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('content_tags')
    op.drop_index(op.f('ix_content_title'), table_name='content')
    op.drop_index(op.f('ix_content_slug'), table_name='content')
    op.drop_index(op.f('ix_content_id'), table_name='content')
    op.drop_table('content')
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    op.drop_index(op.f('ix_tags_id'), table_name='tags')
    op.drop_table('tags')
    # ### end Alembic commands ###
