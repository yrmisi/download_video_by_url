import logging
import uuid

from fastapi import APIRouter, Request

from app.core.limiter import limiter
from app.core.task_registry import running_task
from app.database import session_pool
from app.dependencies import AsyncRedisDep, RedisDep
from app.schemas import LoadMediaRequest
from app.services import (
    DownloadTaskService,
    get_download_status,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status/{task_id}")
async def get_status(
    task_id: str,
    r: AsyncRedisDep,
) -> dict[str, str]:
    """
    Endpoint to check the status of a download task.
    """
    return await get_download_status(task_id, r)


@router.post("/download")
@limiter.limit("5/minute")
async def load_media(
    request: Request,
    load_media: LoadMediaRequest,
    r: RedisDep,
) -> dict[str, str]:
    """
    Endpoint to initiate a media download.
    """
    task_id: str = str(uuid.uuid7())
    download_task = DownloadTaskService(
        task_id,
        session_pool,
        load_media,
        r,
    )
    await running_task(task_id, download_task)
    return {"task_id": task_id}
