import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.database_url
SECRET_KEY = settings.secret_key

# Environment-based configurations with optimized pooling
if settings.environment == "production":
    # Production: Larger pool with pre-ping for connection health
    engine = create_async_engine(
        settings.database_url,
        pool_size=20,  # Number of connections to keep open
        max_overflow=50,  # Extra connections when pool is exhausted
        pool_timeout=60,  # Wait time for connection from pool
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_pre_ping=True,  # Check connection health before using
        echo=False,
    )
elif settings.environment == "test":
    # Test: Use NullPool to avoid connection issues in tests
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,  # No connection pooling for tests
        echo=False,
    )
else:
    # Development: Moderate pool with query logging
    engine = create_async_engine(
        settings.database_url,
        echo=True,  # Enable query logging in dev mode
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_pre_ping=True,  # Check connection health
    )

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    logging.info("Opening database session...")
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"Database session error: {e}")
            raise
        finally:
            try:
                await db.close()
                logging.info("Database session closed.")
            except Exception as close_error:
                logger.warning(f"Error closing database session: {close_error}")


# async def get_async_session() -> AsyncSession:
#     async with async_session() as session:
#         yield session
