from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


engine: AsyncEngine = create_async_engine(settings.database_url, echo=settings.debug, future=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope for async DB operations."""
    async with async_session_maker() as session:
        yield session


__all__ = ["Base", "async_session_maker", "get_db", "engine"]
