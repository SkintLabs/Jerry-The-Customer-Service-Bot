"""
================================================================================
Jerry The Customer Service Bot — Database Engine
================================================================================
File:     app/db/engine.py
Version:  1.0.0
Session:  5 (February 2026)

PURPOSE
-------
Async SQLAlchemy engine and session factory. Reads DATABASE_URL from .env.
Supports both SQLite (local dev) and PostgreSQL (production on Railway).

USAGE
-----
    from app.db.engine import get_db, init_db

    # In lifespan:
    await init_db()

    # In route handlers:
    async with get_db() as db:
        store = await db.get(Store, 1)
================================================================================
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from dotenv import load_dotenv

from app.db.models import Base

load_dotenv()

logger = logging.getLogger("sunsetbot.db")

# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sunsetbot.db")

# Railway provides PostgreSQL URLs as "postgresql://..." but asyncpg needs
# "postgresql+asyncpg://..." — auto-fix here so it works out of the box.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# SQLite needs special connect args for async
_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "").lower() == "true",
    connect_args=_connect_args,
)

# Session factory — produces async sessions
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Create all tables if they don't exist. Call once at startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(f"Database initialized (url={DATABASE_URL.split('://')[0]})")


async def close_db() -> None:
    """Dispose of the engine connection pool. Call on shutdown."""
    await engine.dispose()
    logger.info("Database connection pool closed.")


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.

    Usage:
        async with get_db() as db:
            result = await db.execute(select(Store))
            stores = result.scalars().all()
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
