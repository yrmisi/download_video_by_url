import logging
from typing import Any, Mapping

import yt_dlp

logger = logging.getLogger(__name__)


def get_raw_extract_info(
    url: str,
    opts: Any,
    download_allowed: bool = False,
) -> Mapping[str, Any]:
    """
    Basic wrapper over yt-dlp.
    """
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=download_allowed)


def execute_ydl(
    opts: Any,
    url: str,
    download_allowed: bool = True,
) -> tuple[Mapping[str, Any], str]:
    """
    A synchronous function to run in ThreadPoolExecutor.
    Returns (info_dict, prepared_filename).
    """
    with yt_dlp.YoutubeDL(opts) as ydl:
        # Скачиваем и получаем инфо за один проход
        result = ydl.extract_info(url, download=download_allowed)
        # Сразу готовим финальное имя файла внутри потока
        full_path = ydl.prepare_filename(result)
        return result, full_path
