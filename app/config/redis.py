from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .paths import ENVS_DIR


class RedisConfig(BaseSettings):
    """
    Redis service configuration.
    """

    password: Annotated[str | None, Field(alias="REDIS_PASSWORD")] = None
    host: Annotated[str, Field(alias="REDIS_HOST")] = "localhost"
    port: Annotated[int, Field(alias="REDIS_PORT")] = 6379
    db: int = 0
    decode_responses: bool = True
    max_connections: Annotated[int, Field(alias="REDIS_MAX_CONNECTIONS")] = 10
    health_check_interval: Annotated[int, Field(alias="REDIS_HEALTH_CHECK_INTERVAL")] = 0

    model_config = SettingsConfigDict(
        env_file=ENVS_DIR / ".env.redis-prod",
        env_file_encoding="utf-8",
        extra="ignore",
    )
