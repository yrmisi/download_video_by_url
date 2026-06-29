"""
Схемы валидации входящих запросов на загрузку медиаконтента.
"""

import re
from enum import Enum
from typing import Any

from pydantic import AnyUrl, BaseModel, field_validator

from app.config import settings


class Quality(str, Enum):
    """
    List of available video and audio resolutions for download.
    """

    p2160 = "2160"
    p1440 = "1440"
    p1080 = "1080"
    p720 = "720"
    p360 = "360"
    p240 = "240"
    p144 = "144"
    bestaudio = "bestaudio"


class DownloadProfile(str, Enum):
    """
    Conversion profiles for different device types and formats.
    """

    pc_tv = "pc_tv"  # Максимальное качество (VP9/AV1, 4K, MKV)
    legacy_tv = "legacy_tv"  # Для старых Samsung/LG (H.264, MP4)
    mobile = "mobile"  # Экономно и быстро (720p, MP4)
    mp4 = "mp4"  # Готовый один файл без сборки (1080p, MP4)
    audio = "audio_only"


class LoadMediaRequest(BaseModel):
    """
    Request schema for loading media.
    """

    url: AnyUrl
    user_id: str | None = None
    profile: DownloadProfile = DownloadProfile.pc_tv
    quality: str | None = None

    @field_validator("url", mode="before")
    @classmethod
    def sanitize_media_url(cls, value: Any) -> Any:
        """
        Cleans YouTube links of junk, but passes links to other sites (VK, etc.) unchanged.
        """

        # Приводим значение к строке для анализа
        url_str: str = ""
        if isinstance(value, str):
            url_str = value
        elif hasattr(value, "unicode_string"):
            url_str = value.unicode_string()
        else:
            return value

        # Проверяем, является ли ссылка ютубовской
        is_youtube: bool = any(domain in url_str.lower() for domain in ["youtube.com", "youtu.be"])

        if is_youtube:
            # Ищем строго 11 символов ID видео YouTube
            video_id_match = re.search(
                r"(?:v=|\/v\/|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})", url_str
            )
            if video_id_match:
                video_id = video_id_match.group(1)
                return settings.app.base_url_yt.format(video_id=video_id)

        return url_str
