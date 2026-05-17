from pydantic import BaseModel

from .app import AppConfig
from .database import DatabaseConfig
from .redis import RedisConfig


class Settings(BaseModel):
    """
    Application service settings.
    """

    redis: RedisConfig = RedisConfig()
    db: DatabaseConfig = DatabaseConfig()
    app: AppConfig = AppConfig()


settings = Settings()
