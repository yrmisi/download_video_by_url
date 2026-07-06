from contextvars import ContextVar
from typing import Optional

# Переменная, которая будет хранить ID запроса для текущего асинхронного потока
ctx_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
