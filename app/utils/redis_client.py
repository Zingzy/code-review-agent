import redis
import redis.asyncio as aioredis
from app.config.settings import get_settings

settings = get_settings()


def get_sync_redis_client():
    """
    Provides a synchronous Redis client connection.
    """
    return redis.from_url(settings.redis.url, encoding="utf-8", decode_responses=False)


async def get_async_redis_client():
    """
    Provides an asynchronous Redis client connection.
    """
    return aioredis.from_url(
        settings.redis.url, encoding="utf-8", decode_responses=True
    )
