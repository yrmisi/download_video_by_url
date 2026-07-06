import logging.config
import sys
from typing import Any

from app.config.settings import settings

from .formatters import CustomJSONFormatter


def setup_logging() -> None:
    """
    Function for initializing logging throughout the application.
    """

    logging_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,  # Не ломаем логгеры uvicorn/granian
        "formatters": {
            "json": {
                "()": CustomJSONFormatter,
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json",
            },
        },
        "loggers": {
            # Корневой логгер приложения
            "app": {
                "handlers": ["stdout"],
                "level": settings.app.log_level,
                "propagate": False,
            },
            # При желании можно завернуть логи самого Uvicorn/Granian в JSON
            "granian.error": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
            "granian.access": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        },
        # Настройки для всех остальных внешних библиотек (SQLAlchemy, Redis и т.д.)
        "root": {
            "handlers": ["stdout"],
            "level": "WARNING",
        },
    }

    logging.config.dictConfig(logging_config)
