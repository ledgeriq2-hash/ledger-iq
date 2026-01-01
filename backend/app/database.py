from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


def _create_engine(database_url: str) -> AsyncEngine:
    url = make_url(database_url)
    kwargs: dict[str, Any] = {"echo": settings.debug, "future": True}
    if url.drivername.startswith("sqlite"):
        kwargs["poolclass"] = NullPool
    return create_async_engine(database_url, **kwargs)


engine: AsyncEngine = _create_engine(settings.database_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope for async DB operations."""
    async with async_session_maker() as session:
        yield session


async def dispose_engine() -> None:
    """Dispose the async engine and close all pooled connections."""
    await engine.dispose()


__all__ = ["Base", "async_session_maker", "get_db", "engine", "dispose_engine"]
