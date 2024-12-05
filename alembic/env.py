from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from alembic import context

from app.database import Base
from app.models.user import User
from app.models.content import Content
from app.models.tag import Tag
from app.models.activity_log import ActivityLog
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
    return config.get_main_option("sqlalchemy.url")

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using AsyncEngine."""
    connectable: AsyncEngine = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            context.configure,
            connection=connection,
            target_metadata=target_metadata,
        )

        async with context.begin_transaction():
            await connection.run_sync(context.run_migrations)

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
