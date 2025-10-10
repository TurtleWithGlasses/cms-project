from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = settings.database_url
SECRET_KEY = settings.secret_key

# Environment-based configurations
if settings.environment == "production":
    engine = create_async_engine(
        settings.database_url,
        pool_size=20,
        max_overflow=50,
        pool_timeout=60,
        pool_recycle=1800,
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=True,  # Enable query logging in dev mode
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
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