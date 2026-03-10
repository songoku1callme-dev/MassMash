"""Perfect School 4.1 Block 6: PostgreSQL + Redis scaffolding.

When POSTGRES_URL and/or REDIS_URL are set, these helpers provide
async connection pools ready for production use.

Currently the app uses SQLite via aiosqlite. This module prepares
the migration path to PostgreSQL + Redis without breaking existing code.

Usage (future):
    from app.core.postgres_redis import get_pg_pool, get_redis

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM users")

    redis = await get_redis()
    await redis.set("key", "value", ex=3600)
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

POSTGRES_URL = os.getenv("POSTGRES_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")

# Lazy-initialized connection pools
_pg_pool = None
_redis_client = None


async def get_pg_pool():
    """Get or create an asyncpg connection pool.

    Requires: pip install asyncpg
    Set POSTGRES_URL=postgresql://user:pass@host:5432/dbname
    """
    global _pg_pool
    if not POSTGRES_URL:
        logger.debug("POSTGRES_URL not set — PostgreSQL disabled.")
        return None

    if _pg_pool is None:
        try:
            import asyncpg  # type: ignore[import-untyped]
            _pg_pool = await asyncpg.create_pool(
                POSTGRES_URL,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info("PostgreSQL pool created successfully.")
        except ImportError:
            logger.warning("asyncpg not installed. Run: pip install asyncpg")
            return None
        except Exception as e:
            logger.error("Failed to create PostgreSQL pool: %s", e)
            return None

    return _pg_pool


async def get_redis():
    """Get or create a Redis client.

    Requires: pip install redis[hiredis]
    Set REDIS_URL=redis://localhost:6379/0
    """
    global _redis_client
    if not REDIS_URL:
        logger.debug("REDIS_URL not set — Redis disabled.")
        return None

    if _redis_client is None:
        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]
            _redis_client = aioredis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
            )
            # Test connection
            await _redis_client.ping()
            logger.info("Redis client connected successfully.")
        except ImportError:
            logger.warning("redis not installed. Run: pip install redis[hiredis]")
            return None
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            return None

    return _redis_client


async def close_pools():
    """Gracefully close connection pools on shutdown."""
    global _pg_pool, _redis_client
    if _pg_pool is not None:
        await _pg_pool.close()
        _pg_pool = None
        logger.info("PostgreSQL pool closed.")
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed.")


# --- Cache helpers (use Redis if available, else in-memory) ---

_memory_cache: dict = {}


async def cache_get(key: str) -> Optional[str]:
    """Get a cached value (Redis or in-memory fallback)."""
    r = await get_redis()
    if r:
        return await r.get(key)
    return _memory_cache.get(key)


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    """Set a cached value with TTL in seconds."""
    r = await get_redis()
    if r:
        await r.set(key, value, ex=ttl)
    else:
        _memory_cache[key] = value


async def cache_delete(key: str) -> None:
    """Delete a cached value."""
    r = await get_redis()
    if r:
        await r.delete(key)
    else:
        _memory_cache.pop(key, None)
