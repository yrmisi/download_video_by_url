import json
from typing import Any

from redis import Redis
from yt_dlp.utils import DownloadError

from app.config import settings


def check_cancel_status(task_id: str, redis_client: Redis) -> None:
    """
    Check if a cancellation mark has appeared in Redis.
    """

    status_data: Any = redis_client.get(f"task:{task_id}")
    if status_data:
        status = json.loads(status_data).get("status")
        # Проверяем метку отмены ("cancelled")
        if status == settings.app.state.cancel:
            # Выбрасываем системную ошибку yt-dlp, которую его постпроцессоры не смогут проигнорировать
            raise DownloadError("Download cancelled by user")
