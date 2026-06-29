import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, status
from yt_dlp.utils import DownloadError

from app.dependencies import AsyncRedisDep
from app.schemas import LoadMediaRequest, MediaInfo
from app.services import MediaInfoService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/extract-info")
async def extract_info(
    load_media: LoadMediaRequest,
    async_r: AsyncRedisDep,
) -> dict[str, str | int]:
    """
    Endpoint to extract media information from a URL.
    """

    try:
        service: MediaInfoService = MediaInfoService(async_r)
        media_info: MediaInfo = await service.get_media_info(str(load_media.url))
        return asdict(media_info)
    except DownloadError as e:
        logger.error(f"Error yt-dlp while parsing URL {load_media.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to connect to the streaming service. Please try again later or check the link.",
        )
