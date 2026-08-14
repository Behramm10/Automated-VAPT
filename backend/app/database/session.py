"""
Database session management — async SQLAlchemy 2.x.

Supports both PostgreSQL (production) and SQLite (development).
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = structlog.get_logger(__name__)

# ─── Engine ───────────────────────────────────────────────────────────────────
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize model to dictionary."""
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}


def _build_engine() -> AsyncEngine:
    """Build the async database engine with appropriate settings."""
    db_url = settings.effective_database_url
    is_sqlite = "sqlite" in db_url

    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {
        "echo": settings.db_echo,
    }

    if is_sqlite:
        # SQLite requires check_same_thread=False for async
        connect_args["check_same_thread"] = False
        engine_kwargs["connect_args"] = connect_args
    else:
        # PostgreSQL pool settings
        engine_kwargs["pool_size"] = settings.db_pool_size
        engine_kwargs["max_overflow"] = settings.db_max_overflow
        engine_kwargs["pool_pre_ping"] = True

    logger.info("db_engine_creating", url=db_url.split("://")[0])
    return create_async_engine(db_url, **engine_kwargs)


async def init_db() -> None:
    """Initialize database engine, session factory, and create tables if needed."""
    global _engine, _session_factory

    _engine = _build_engine()
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # For SQLite dev mode, create tables directly (no Alembic required)
    if settings.use_sqlite or settings.app_env == "test":
        import app.database.models  # noqa: F401 — registers all models via __init__.py
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("db_tables_created", mode="sqlite_autocreate")


    logger.info("db_initialized", db=settings.effective_database_url.split("://")[0])


async def close_db() -> None:
    """Dispose database connections."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("db_closed")


def get_engine() -> AsyncEngine:
    """Return the database engine. Must be called after init_db()."""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory. Must be called after init_db()."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.

    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
