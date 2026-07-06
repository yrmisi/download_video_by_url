import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import ctx_request_id


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware for managing end-to-end Request ID (Correlation ID).
    Extracts the ID from the headers or generates a new one, passing it
    into the log context and returning it in the response to the client.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 1. Пытаемся взять существующий ID (от Nginx, Гейтвея или Granian)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 2. Привязываем ID к текущему асинхронному контексту
        token = ctx_request_id.set(request_id)

        try:
            response: Response = await call_next(request)

            # 3. Добавляем ID в заголовки ответа, чтобы фронтенд или клиент могли его прислать при ошибке
            response.headers["X-Request-ID"] = request_id
            return response

        finally:
            # 4. Очищаем контекст после завершения обработки таски
            ctx_request_id.reset(token)
