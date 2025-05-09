"""add content_versions, publish_at, categories

Revision ID: 0a1bf46b926d
Revises: 044b43179099
Create Date: 2025-04-04 18:42:36.595115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0a1bf46b926d'
down_revision: Union[str, None] = '044b43179099'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("UPDATE activity_logs SET user_id = 1 WHERE user_id IS NULL")
    op.alter_column('activity_logs', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('activity_logs', 'timestamp',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('activity_logs', 'description',
               existing_type=sa.VARCHAR(),
               type_=sa.Text(),
               nullable=False)
    op.create_index('idx_content_action_timestamp', 'activity_logs', ['content_id', 'action', 'timestamp'], unique=False)
    op.create_index('idx_user_action_timestamp', 'activity_logs', ['user_id', 'action', 'timestamp'], unique=False)
    op.drop_constraint('activity_logs_user_id_fkey', 'activity_logs', type_='foreignkey')
    op.drop_constraint('activity_logs_content_id_fkey', 'activity_logs', type_='foreignkey')
    op.drop_constraint('activity_logs_target_user_id_fkey', 'activity_logs', type_='foreignkey')
    op.create_foreign_key(None, 'activity_logs', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'activity_logs', 'users', ['target_user_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(None, 'activity_logs', 'content', ['content_id'], ['id'], ondelete='SET NULL')
    op.add_column('content', sa.Column('category_id', sa.Integer(), nullable=True))
    op.alter_column('content', 'title',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('content', 'body',
               existing_type=sa.TEXT(),
               nullable=False)
    # Set default slugs for existing content with NULL slugs
    op.execute("""
        UPDATE content
        SET slug = 'default-slug-' || id
        WHERE slug IS NULL
    """)

    op.alter_column('content', 'slug',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('content', 'meta_title',
               existing_type=sa.VARCHAR(),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('content', 'meta_keywords',
               existing_type=sa.VARCHAR(),
               type_=sa.Text(),
               existing_nullable=True)
    op.create_index('idx_content_status', 'content', ['status'], unique=False)
    op.create_index(op.f('ix_content_author_id'), 'content', ['author_id'], unique=False)
    op.create_foreign_key(None, 'content', 'categories', ['category_id'], ['id'])
    op.create_index('idx_content_tag', 'content_tags', ['content_id', 'tag_id'], unique=False)
    op.drop_constraint('content_tags_tag_id_fkey', 'content_tags', type_='foreignkey')
    op.drop_constraint('content_tags_content_id_fkey', 'content_tags', type_='foreignkey')
    op.create_foreign_key(None, 'content_tags', 'content', ['content_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'content_tags', 'tags', ['tag_id'], ['id'], ondelete='CASCADE')
    op.alter_column('notifications', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('notifications', 'status',
               existing_type=postgresql.ENUM('UNREAD', 'READ', name='notificationstatus'),
               nullable=False)
    op.alter_column('notifications', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.create_index(op.f('ix_notifications_content_id'), 'notifications', ['content_id'], unique=False)
    op.create_index(op.f('ix_notifications_status'), 'notifications', ['status'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.alter_column('roles', 'permissions',
        existing_type=sa.VARCHAR(),
        type_=postgresql.JSON(),
        existing_nullable=False,
        postgresql_using="permissions::json"
)
    op.alter_column('tags', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('users', 'role_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)
    op.create_unique_constraint(None, 'users', ['email'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.create_index('ix_users_username', 'users', ['username'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.alter_column('users', 'role_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
    op.alter_column('tags', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('roles', 'permissions',
               existing_type=sa.JSON(),
               type_=sa.VARCHAR(),
               existing_nullable=False)
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_status'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_content_id'), table_name='notifications')
    op.alter_column('notifications', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('notifications', 'status',
               existing_type=postgresql.ENUM('UNREAD', 'READ', name='notificationstatus'),
               nullable=True)
    op.alter_column('notifications', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_constraint(None, 'content_tags', type_='foreignkey')
    op.drop_constraint(None, 'content_tags', type_='foreignkey')
    op.create_foreign_key('content_tags_content_id_fkey', 'content_tags', 'content', ['content_id'], ['id'])
    op.create_foreign_key('content_tags_tag_id_fkey', 'content_tags', 'tags', ['tag_id'], ['id'])
    op.drop_index('idx_content_tag', table_name='content_tags')
    op.drop_constraint(None, 'content', type_='foreignkey')
    op.drop_index(op.f('ix_content_author_id'), table_name='content')
    op.drop_index('idx_content_status', table_name='content')
    op.alter_column('content', 'meta_keywords',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(),
               existing_nullable=True)
    op.alter_column('content', 'meta_title',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(),
               existing_nullable=True)
    op.alter_column('content', 'slug',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('content', 'body',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('content', 'title',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_column('content', 'category_id')
    op.drop_constraint(None, 'activity_logs', type_='foreignkey')
    op.drop_constraint(None, 'activity_logs', type_='foreignkey')
    op.drop_constraint(None, 'activity_logs', type_='foreignkey')
    op.create_foreign_key('activity_logs_target_user_id_fkey', 'activity_logs', 'users', ['target_user_id'], ['id'])
    op.create_foreign_key('activity_logs_content_id_fkey', 'activity_logs', 'content', ['content_id'], ['id'])
    op.create_foreign_key('activity_logs_user_id_fkey', 'activity_logs', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.drop_index('idx_user_action_timestamp', table_name='activity_logs')
    op.drop_index('idx_content_action_timestamp', table_name='activity_logs')
    op.alter_column('activity_logs', 'description',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(),
               nullable=True)
    op.alter_column('activity_logs', 'timestamp',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('activity_logs', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###
