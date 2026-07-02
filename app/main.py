import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import setup_logging
from app.core.cors import get_allowed_origins
from app.core.handlers import (
    rate_limit_handler,
    validation_exception_handler,
)
from app.core.limiter import limiter
from app.database import async_engine
from app.routers import (
    cancel_router,
    health_router,
    history_router,
    load_files_router,
    load_media_router,
    media_info_router,
)
from app.services import FileCleanupService

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan for the application.
    """
    # Читаем флаг из окружения. По умолчанию выключен, чтобы случайно не запустить на dev в 4 воркера
    run_cleanup = os.getenv("RUN_BACKGROUND_TASKS", "False").lower() in ("true", "1", "yes")

    shutdown_event = None

    if run_cleanup:
        logger.info("Starting up background cleanup tasks (Worker mode)...")

        # Создаем ивент для сигнализации о закрытии приложения
        shutdown_event = asyncio.Event()
        app.state.shutdown_event = shutdown_event

        cleanup_service = FileCleanupService()

        # Передаем ивент в задачи (или сам сервис)
        app.state.cleanup_expired_task = asyncio.create_task(
            cleanup_service.clean_expired_downloads(shutdown_event)
        )
        app.state.cleanup_trash_task = asyncio.create_task(
            cleanup_service.clean_daily_trash(shutdown_event)
        )
    else:
        logger.info("Background cleanup tasks are DISABLED (Web server mode).")

    yield

    if run_cleanup and shutdown_event:
        logger.info("Gracefully shutting down cleanup tasks...")

        # Сигнализируем задачам, что пора закругляться
        shutdown_event.set()

        # Ждем, пока они завершат текущую итерацию удаления
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    app.state.cleanup_expired_task,
                    app.state.cleanup_trash_task,
                    return_exceptions=True,
                ),
                timeout=10.0,  # 10 секунд более чем достаточно для удаления файлов
            )
        except asyncio.TimeoutError:
            logger.warning("Cleanup tasks did not finish gracefully in time, forcing cancel")
            app.state.cleanup_expired_task.cancel()
            app.state.cleanup_trash_task.cancel()
            await asyncio.gather(
                app.state.cleanup_expired_task,
                app.state.cleanup_trash_task,
                return_exceptions=True,
            )

    # В самую последнюю очередь закрываем коннекты к БД
    await async_engine.dispose()
    logger.info("Application lifespan shutdown complete.")


app = FastAPI(title="MediaGrab", lifespan=lifespan)

# Настройка CORS
# CORS Middleware (ДОЛЖЕН БЫТЬ ПЕРВЫМ для обработки OPTIONS preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "DELETE",
        "OPTIONS",  # OPTIONS нужен для preflight-запросов браузера
    ],
    allow_headers=["*"],
)

# Интегрируем SlowAPI
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Регистрация обработчиков исключений
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(router=health_router)
app.include_router(router=media_info_router, prefix="/api")
app.include_router(router=load_media_router, prefix="/api")
app.include_router(router=history_router, prefix="/api")
app.include_router(router=cancel_router, prefix="/api")
app.include_router(router=load_files_router, prefix="/api")

# Инициализируем сбор метрик (подсчет HTTP запросов, ошибок, latency)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# for development
# app.mount("/files", StaticFiles(directory=DOWNLOADS_DIR), name="files")
# app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# templates = Jinja2Templates(directory=STATIC_DIR)


# @app.get("/", response_class=HTMLResponse)
# async def index(request: Request):
#     """ """
#     return templates.TemplateResponse(
#         request=request,
#         name="index.html",
#     )
