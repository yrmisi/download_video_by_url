from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.config import settings


@lru_cache
def get_async_redis() -> Redis:
    """
    Return a cached asyncio Redis client instance configured from application settings.
    """

    return Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        db=settings.redis.db,
        password=settings.redis.password,
        decode_responses=settings.redis.decode_responses,
        max_connections=settings.redis.max_connections,
        health_check_interval=settings.redis.health_check_interval,
    )

AsyncRedisDep = Annotated[Redis, Depends(get_async_redis)]
