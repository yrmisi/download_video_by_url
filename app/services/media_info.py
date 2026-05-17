import logging

from app.config import settings
from app.core.ytdlp.executor import get_raw_extract_info
from app.schemas import MediaInfo

logger = logging.getLogger(__name__)


def get_media_info(url: str) -> MediaInfo:
    """
    Retrieve basic metadata for a given URL.
    """
    info = get_raw_extract_info(
        url,
        settings.app.base_ydl_opts,
        download_allowed=False,
    )

    return MediaInfo(
        title=info.get("title") or "Unknown",
        thumbnail=info.get("thumbnail") or "",
        max_quality=info.get("height") or 1080,
    )
