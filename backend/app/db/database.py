from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from ..core.config import settings

Base = declarative_base()
engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    global engine
    if engine is None:
        engine = create_async_engine(
            settings.database_url(),
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return AsyncSessionLocal


async def get_db():
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
