import logging
from typing import cast

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def rate_limit_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    # Получаем IP клиента (с учетом возможного Nginx прокси)
    client_ip = request.headers.get("X-Forwarded-For") or (
        request.client.host if request.client else "unknown"
    )

    # Логируем событие превышения лимита
    logger.warning(
        "Rate limit exceeded for IP: %s on route: %s [%s]",
        client_ip,
        request.url.path,
        request.method,
    )
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests",
        },
    )


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Pydantic global validation error interceptor (including SSRF).
    """

    # # Преобразуем тип
    validation_exc = cast(RequestValidationError, exc)
    errors = validation_exc.errors()

    # Логируем попытку подозрительного запроса для истории
    logger.warning("Validation error occurred for URL: %s. Errors: %s", request.url, errors)

    for error in errors:
        # Проверяем наш кастомный тип ошибки из Pydantic валидатора
        if error.get("type") == "ssrf_error":
            return JSONResponse(
                status_code=400, content={"detail": error.get("msg") or "Недопустимый URL-адрес"}
            )

    # Для всех остальных стандартных ошибок оставляем 422
    return JSONResponse(status_code=422, content={"detail": errors})
