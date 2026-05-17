import json
import logging
from typing import Any

from redis import Redis

from app.core.redis_status import check_cancel_status

logger = logging.getLogger(__name__)


def progress_hook(
    d: dict[str, Any],
    task_id: str,
    redis_client: Redis,
) -> None:
    """
    Monitoring the download process.
    """

    logger.info(f"Progress hook called: {d.get('status')} - {d.get('_percent_str')}")

    check_cancel_status(task_id, redis_client)

    if d['status'] == 'downloading':
        data = {
            "percent": d.get('_percent_str', '0%'),
            "speed": d.get('_speed_str', 'N/A'),
            "status": "downloading",
        }

        try:
            # Сохраняем в Redis с временем жизни 1 час (чтобы не мусорить)
            redis_client.setex(
                f"task:{task_id}",
                3600,
                json.dumps(data),
            )
            logger.info(f"Saved to Redis: {data}")
        except Exception as e:
            logger.error(f"Redis error: {e}")


def postprocessor_hook(
    d: dict[str, Any],
    task_id: str,
    redis_client: Redis,
) -> None:
    """
    Monitoring FFmpeg performance (merging, thumbnails).
    """

    logger.info(f"Post-processor hook: {d.get('status')} - {d.get('postprocessor')}")

    check_cancel_status(task_id, redis_client)

    status_msg = "Processing..."
    if d['status'] == 'started':
        # Можно уточнить, какой именно процесс идет
        pp_name = d.get('postprocessor', '')
        if pp_name == 'Merger':
            status_msg = "Merging video & audio..."
        elif pp_name == 'EmbedThumbnail':
            status_msg = "Adding thumbnail..."
        elif pp_name == 'FFmpegMetadata':
            status_msg = "Writing metadata..."

        data = {
            "percent": "100%",  # Визуально оставляем заполненным
            "speed": "FFmpeg",
            "status": "processing",  # Меняем статус на processing
            "msg": status_msg,
        }
        try:
            redis_client.setex(
                f"task:{task_id}",
                3600,
                json.dumps(data),
            )
            logger.info(f"Saved processing status: {data}")
        except Exception as e:
            logger.error(f"Redis error: {e}")
