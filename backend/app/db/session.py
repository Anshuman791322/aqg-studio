"""Database async engine and session lifecycle management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine | None:
    """Return singleton async SQLAlchemy engine, initializing if DATABASE_URL is set."""
    global _async_engine, _async_session_factory
    if _async_engine is None and settings.DATABASE_URL:
        db_url = settings.DATABASE_URL
        # Ensure asyncpg driver prefix
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

        _async_engine = create_async_engine(
            db_url,
            echo=settings.DB_ECHO_LOG,
            future=True,
            pool_pre_ping=True,
        )
        _async_session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """Return session factory."""
    if _async_session_factory is None:
        get_engine()
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession | None, None]:
    """FastAPI dependency yielding an async database session or None if not configured."""
    factory = get_session_factory()
    if factory is None:
        yield None
        return

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_health() -> bool:
    """Perform a ping against the database to check connectivity."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False
