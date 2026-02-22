import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.database_url
SECRET_KEY = settings.secret_key

# ---------------------------------------------------------------------------
# Primary (write) engine — environment-based pool configuration
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Read replica engine — optional; falls back to primary when not configured.
# Routes using get_read_db() must only perform SELECT operations.
# ---------------------------------------------------------------------------
if settings.database_read_replica_url:
    if settings.environment == "production":
        read_engine = create_async_engine(
            settings.database_read_replica_url,
            pool_size=20,
            max_overflow=50,
            pool_timeout=60,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False,
        )
    elif settings.environment == "test":
        read_engine = create_async_engine(
            settings.database_read_replica_url,
            poolclass=NullPool,
            echo=False,
        )
    else:
        read_engine = create_async_engine(
            settings.database_read_replica_url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_pre_ping=True,
            echo=False,
        )
else:
    # No replica configured — reads go to the primary (identical to pre-5.4 behaviour)
    read_engine = engine

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
)

ReadAsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=read_engine,
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


async def get_read_db():
    """
    Read-only database session dependency.

    Uses the read replica engine when DATABASE_READ_REPLICA_URL is set;
    falls back to the primary engine otherwise.  Only inject this dependency
    into endpoints that perform SELECT operations — any writes must use get_db().
    Note: replica data may lag the primary by a small amount (<100 ms typical).
    """
    async with ReadAsyncSessionLocal() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"Read-DB session error: {e}")
            raise
        finally:
            try:
                await db.close()
            except Exception as close_error:
                logger.warning(f"Error closing read-DB session: {close_error}")


def get_pool_stats() -> dict:
    """
    Return connection-pool statistics for the primary and read-replica engines.

    Uses SQLAlchemy's sync pool introspection (engine.sync_engine.pool).
    Returns zeros for NullPool (test environment) where pool stats are unavailable.
    """

    def _stats(eng) -> dict:
        pool = eng.sync_engine.pool
        # NullPool has no size/checkin/checkout counters
        if isinstance(pool, NullPool):
            return {"size": 0, "checkedin": 0, "checkedout": 0, "overflow": 0}
        try:
            return {
                "size": pool.size(),
                "checkedin": pool.checkedin(),
                "checkedout": pool.checkedout(),
                "overflow": pool.overflow(),
            }
        except Exception:
            return {"size": 0, "checkedin": 0, "checkedout": 0, "overflow": 0}

    return {
        "primary": _stats(engine),
        "replica": _stats(read_engine),
    }


# async def get_async_session() -> AsyncSession:
#     async with async_session() as session:
#         yield session


@asynccontextmanager
async def get_db_context():
    """Context manager for database sessions (for use outside of FastAPI dependencies)."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"Database session error: {e}")
            raise
        finally:
            try:
                await db.close()
            except Exception as close_error:
                logger.warning(f"Error closing database session: {close_error}")
