import asyncio
import json
import logging
import os

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.paths import DOWNLOADS_DIR
from app.core.task_registry import active_tasks
from app.core.ytdlp.executor import get_raw_extract_info
from app.database.models import DownloadTask
from app.repositories import DownloadHistoryRepository
from app.schemas import UpdateLoadHistoryItems

logger = logging.getLogger(__name__)


class StoppedTaskServices:
    """
    Service for stopping and cleaning up active tasks.
    """

    def __init__(self, session: AsyncSession, r: Redis) -> None:
        """
        Initialize the stopped task service.
        """
        self.repo = DownloadHistoryRepository(session)
        self.r = r

    async def stop_download(self, task_id: str) -> None:
        """
        Cancel an active download task and clean up files.
        """
        # Пишем статус в Redis, чтобы хуки yt-dlp (если они выполняются прямо сейчас)
        # мгновенно увидели команду на остановку при следующей проверке.
        await self.r.setex(
            f"task:{task_id}",
            3600,  # Увеличим TTL для истории до 1 часа
            json.dumps(
                {
                    "status": settings.app.state.cancel,
                    "msg": "Stopped by user",
                }
            ),
        )

        # Посылаем CancelledError в корутину
        task = active_tasks.get(task_id)
        if task:
            task.cancel()
            # Даем event loop переключить контекст и запустить цепочку отмены в воркере
            await asyncio.sleep(0)

        media: DownloadTask | None = await self.repo.get_by_id(task_id)

        if media is None:
            logger.warning(f"Task with id {task_id} not found for cancellation.")
            return

        # Безопасный асинхронный вызов метаданных (не блокирует поток сервера)
        try:
            loop = asyncio.get_running_loop()
            info = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    get_raw_extract_info,
                    media.url,
                    settings.app.base_ydl_opts,
                    False,
                ),
                timeout=15.0,  # Жесткий тайм-аут, если сайт завис
            )
            title = info.get("title") or "unknown"
            thumbnail = info.get("thumbnail") or "unknown"
            duration = info.get("duration") or 0
        except Exception as e:
            logger.warning(f"Could not fetch metadata during cancellation for task {task_id}: {e}")
            title, thumbnail, duration = "unknown", "unknown", 0

        # Обновляем статус в базе данных
        item = UpdateLoadHistoryItems(
            title=title,
            thumbnail=thumbnail,
            duration=duration,
            status=settings.app.state.cancel,
        )
        await self.repo.update(task_id, item)

        # Чистим остаточные файлы на диске
        self._cleanup_task_files(task_id)

    @staticmethod
    def _cleanup_task_files(task_id: str) -> None:
        """
        Deletes all files associated with task_id (including .part, .ytdl, .jpg).
        """
        try:
            if not DOWNLOADS_DIR.exists():
                return

            count: int = 0
            for f in os.listdir(DOWNLOADS_DIR):
                if f.startswith(task_id):
                    file_path = DOWNLOADS_DIR / f
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            count += 1
                    except OSError as e:
                        logger.error(f"Error deleting file {file_path}: {e}")

            if count > 0:
                logger.info(f"Cleanup finished: removed {count} files for task {task_id}")
        except Exception as e:
            logger.error(f"Cleanup failed for {task_id}: {e}")
