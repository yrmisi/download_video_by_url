from typing import Annotated

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from .paths import ENVS_DIR


class SQLAlchemyConfig(BaseModel):
    """
    Configuration for SQLAlchemy.
    """

    pool_pre_ping: bool = True
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False


class SessionPollConfig(BaseModel):
    """
    Configuration for SQLAlchemy session behavior.
    """

    autoflush: bool = False
    expire_on_commit: bool = False


class DatabaseConfig(BaseSettings):
    """
    Configuration for the database.
    """

    drivername: str = "postgresql+asyncpg"
    user: Annotated[str, Field(alias="POSTGRES_USER")] = "user"
    password: Annotated[SecretStr, Field(alias="POSTGRES_PASSWORD")] = SecretStr("")
    host: Annotated[str, Field(alias="POSTGRES_HOST")] = "localhost"
    port: int = 5432
    name: Annotated[str, Field(alias="POSTGRES_DB")] = "media_grab"
    sqla: SQLAlchemyConfig = SQLAlchemyConfig()
    poll: SessionPollConfig = SessionPollConfig()

    model_config = SettingsConfigDict(
        env_file=ENVS_DIR / ".env.postgres-prod",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def url_sqla_async(self) -> URL:
        """
        Create async SQLAlchemy database URL.
        """
        return URL.create(
            drivername=self.drivername,
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.name,
        )
