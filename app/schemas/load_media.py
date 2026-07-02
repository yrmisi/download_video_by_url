"""
Схемы валидации входящих запросов на загрузку медиаконтента.
"""

import ipaddress
import re
import socket
from enum import Enum
from typing import Any

from pydantic import AnyUrl, BaseModel, field_validator
from pydantic_core import PydanticCustomError

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

    @field_validator("url", mode="after")
    @classmethod
    def validate_ssrf(cls, url: AnyUrl) -> AnyUrl:
        """
        Protects against SSRF by blocking local, private, and loopback IP addresses/hosts.
        """
        host = url.host

        if not host:
            raise PydanticCustomError("url_error", "URL must contain a valid host")

        # 1. Сразу блокируем явные локальные имена
        host_lower = host.lower()
        if host_lower in ["localhost", "localhost.localdomain"] or host_lower.endswith(".local"):
            raise PydanticCustomError("ssrf_error", "Access to local networks is forbidden")

        # Блокируем имена контейнеров в docker compose сети (db, redis, nginx и т.д.)
        if host_lower in ["db", "redis", "nginx", "web"]:
            raise PydanticCustomError("ssrf_error", "Access to internal services is forbidden")

        # 2. Резолвим хост (IP или домен) в реальный IP-адрес
        try:
            ip_str = socket.gethostbyname(host)
            ip = ipaddress.ip_address(ip_str)
        except Exception:
            # Если домен не резолвится, yt-dlp всё равно не сможет скачать,
            # но для безопасности можно пропустить или выбросить ошибку
            return url

        # 3. Проверяем, входит ли IP в приватные или loopback диапазоны
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
            raise PydanticCustomError("ssrf_error", "Access to private IP ranges is forbidden")

        return url
