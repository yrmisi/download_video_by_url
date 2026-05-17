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
        task = active_tasks.get(task_id)
        if task:
            # Это посылает CancelledError внутрь корутины run_download
            task.cancel()

        await self.r.setex(
            f"task:{task_id}",
            60,
            json.dumps(
                {
                    "status": settings.app.state.cancel,
                    "msg": "Stopped by user",
                }
            ),
        )
        media: DownloadTask | None = await self.repo.get_by_id(task_id)

        if media is None:
            logger.warning(f"Task with id {task_id} not found for cancellation.")
            return

        info = get_raw_extract_info(
            media.url,
            settings.app.base_ydl_opts,
            download_allowed=False,
        )

        item = UpdateLoadHistoryItems(
            title=info.get("title") or "unknown",
            thumbnail=info.get("thumbnail") or "unknown",
            duration=info.get("duration") or 0,
            status=settings.app.state.cancel,
        )

        await self.repo.update(task_id, item)

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
