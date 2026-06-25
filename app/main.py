import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan for the application.
    """
    logger.info("Starting up background cleanup tasks...")

    cleanup_service = FileCleanupService()

    app.state.cleanup_expired_task = asyncio.create_task(cleanup_service.clean_expired_downloads())
    app.state.cleanup_trash_task = asyncio.create_task(cleanup_service.clean_daily_trash())

    yield

    await async_engine.dispose()

    logger.info("Shutting down background cleanup tasks...")
    app.state.cleanup_expired_task.cancel()
    app.state.cleanup_trash_task.cancel()
    await asyncio.gather(
        app.state.cleanup_expired_task,
        app.state.cleanup_trash_task,
        return_exceptions=True,
    )


app = FastAPI(title="MediaGrab", lifespan=lifespan)

# Интегрируем SlowAPI
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests",
        },
    )


app.include_router(router=health_router)
app.include_router(router=media_info_router, prefix="/api")
app.include_router(router=load_media_router, prefix="/api")
app.include_router(router=history_router, prefix="/api")
app.include_router(router=cancel_router, prefix="/api")
app.include_router(router=load_files_router, prefix="/api")

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
