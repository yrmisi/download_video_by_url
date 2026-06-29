import json
import logging.config
import sys
from typing import Any

from .settings import settings


class CustomJSONFormatter(logging.Formatter):
    """
    A custom formatter for creating structured JSON logs.
    """

    def format(self, record: logging.LogRecord) -> str:

        # Базовые поля, которые пригодятся для аналитики (Kibana/Grafana Loki)
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func_name": record.funcName,
            "line_no": record.lineno,
        }

        # Если в лог передали exception (logger.exception или exc_info=True)
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Если передали extra-поля, например: logger.info("text", extra={"user_id": 1})
        # Безопасно вытаскиваем их, игнорируя встроенные атрибуты LogRecord
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs:
                log_record[key] = value

        return json.dumps(log_record, ensure_ascii=False)


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
