from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from alembic import context

from app.database import Base
from app.config import settings
from app.models.content import Content
from app.models.user import User
from app.models.tag import Tag
from app.routes.roles import Role
from app.models.notification import Notification
from app.models.activity_log import ActivityLog
from app.models.category import Category
from app.models.content_version import ContentVersion
from app.models.content_tags import content_tags


# Alembic configuration
config = context.config

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Link target metadata for autogenerate support
target_metadata = Base.metadata

# Retrieve database URL from the configuration
def get_url() -> str:
    return settings.database_url

async def run_migrations_online():
    """Run migrations in 'online' mode using AsyncEngine."""
    connectable = create_async_engine(get_url(), future=True)

    async with connectable.connect() as connection:
        def do_run_migrations(sync_connection):
            context.configure(
                connection=sync_connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
        
        await connection.run_sync(do_run_migrations)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# Choose offline or online mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
