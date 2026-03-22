"""Database session management."""

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# Create async engine
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Create sync engine for Celery tasks
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create sync session factory
sync_session_factory = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.

    Yields:
        AsyncSession: SQLAlchemy async session

    Usage:
        async for session in get_db_session():
            # use session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for FastAPI dependency injection
get_db = get_db_session

# Alias for async session factory (used by worker tasks)
AsyncSessionLocal = async_session_factory


def get_sync_session() -> Generator[Session, None, None]:
    """
    Get a synchronous database session.

    For use in Celery tasks and other sync contexts.

    Yields:
        Session: SQLAlchemy sync session
    """
    session = sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
