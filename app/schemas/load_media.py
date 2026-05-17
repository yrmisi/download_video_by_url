from enum import Enum

from pydantic import AnyUrl, BaseModel


class Quality(str, Enum):
    """ """

    p2160 = "2160"
    p1440 = "1440"
    p1080 = "1080"
    p720 = "720"
    p360 = "360"
    p240 = "240"
    p144 = "144"
    bestaudio = "bestaudio"


class DownloadProfile(str, Enum):
    """ """

    pc_tv = "pc_tv"  # Максимальное качество (VP9/AV1, 4K, MKV)
    legacy_tv = "legacy_tv"  # Для старых Samsung/LG (H.264, MP4)
    mobile = "mobile"  # Экономно и быстро (720p, MP4)
    mp4 = "mp4"  # Готовый один файл без сборки (1080p, MP4)
    audio = "audio_only"


class LoadMediaRequest(BaseModel):
    """ """

    url: AnyUrl
    user_id: str | None = None
    profile: DownloadProfile = DownloadProfile.pc_tv
    quality: str | None = None
