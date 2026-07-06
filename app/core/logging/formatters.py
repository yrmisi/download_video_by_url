import json
import logging

from .context import ctx_request_id


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
        # Автоматически подмешиваем request_id и устанавливаем его в мидлвари
        if request_id := ctx_request_id.get():
            log_record["request_id"] = request_id

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
