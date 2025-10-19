import logging

from sqlalchemy import text

from .db.database import async_engine as engine
from .utils import cache

LOGGER = logging.getLogger(__name__)


async def check_database_health() -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        LOGGER.exception(f"Database health check failed with error: {e}")
        return False


async def check_redis_health() -> bool:
    try:
        if cache.client is None:
            LOGGER.error("Redis client is not initialized")
            return False
        await cache.client.ping()
        return True
    except Exception as e:
        LOGGER.exception(f"Redis health check failed with error: {e}")
        return False
