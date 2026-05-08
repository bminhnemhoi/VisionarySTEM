"""
Async SQLAlchemy session factory + per-request RLS tenant_id setter.

Usage in route handler:
    async with get_session(tenant_id) as session:
        result = await session.execute(...)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from src.config import DATABASE_URL

logger = logging.getLogger(__name__)

_engine = None
_sessionmaker = None


def is_db_enabled() -> bool:
    return bool(DATABASE_URL)


def _ensure_engine():
    global _engine, _sessionmaker
    if _engine is not None:
        return
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set; cannot use DB session")
    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    except ImportError:
        raise RuntimeError(
            "SQLAlchemy 2.0 async not installed. "
            "pip install 'sqlalchemy[asyncio]' asyncpg"
        )
    _engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info(f"DB engine initialized: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'local'}")


@asynccontextmanager
async def get_session(tenant_id: Optional[str] = None) -> AsyncGenerator:
    """
    Yield an async SQLAlchemy session with `app.tenant_id` set for RLS.
    Uses SET LOCAL so it auto-resets at end of transaction.
    """
    _ensure_engine()
    from sqlalchemy import text
    async with _sessionmaker() as session:
        async with session.begin():
            if tenant_id:
                # SET LOCAL only affects current transaction — safe with connection pooling
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tid, true)"),
                    {"tid": tenant_id},
                )
            yield session


async def shutdown_engine():
    global _engine, _sessionmaker
    if _engine:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
        logger.info("DB engine disposed")
