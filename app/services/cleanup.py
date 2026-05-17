import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Sequence

from app.config import settings
from app.config.paths import DOWNLOADS_DIR
from app.database import session_pool
from app.database.models import DownloadTask
from app.repositories import DownloadHistoryRepository

logger = logging.getLogger(__name__)


class FileCleanupService:
    """
    Service for cleaning up expired and junk files.
    """

    def __init__(
        self,
        session_pool=session_pool,
        downloads_dir: Path = DOWNLOADS_DIR,
    ):
        """
        Initialize the file cleanup service.
        """
        self.session_pool = session_pool
        self.downloads_dir = downloads_dir

    async def clean_expired_downloads(self):
        """
        Every 15 minutes, it checks the database for files that have expired within 1 hour of completion and deletes them from the disk, changing their status in the database.
        """
        while True:
            try:
                logger.debug("Checking DB for downloads expired more than 1 hour ago...")

                async with self.session_pool() as session:
                    self.repo = DownloadHistoryRepository(session)
                    expired_tasks: Sequence[DownloadTask] = (
                        await self.repo.get_record_create_hour_ago()
                    )

                    for task in expired_tasks:
                        # 2. Пытаемся удалить файлы по ID задачи
                        # Метод find_and_delete_task_files удалит и видео, и jpg если остались
                        files_deleted = self._delete_files_by_task_id(str(task.id))

                        # 3. Меняем статус в БД на 'deleted', чтобы больше не обрабатывать
                        # и чтобы в истории пользователя было видно, что файл удален по таймауту
                        task.status = settings.app.state.delete
                        logger.info(
                            f"Task {task.id} expired. Status updated to 'deleted'. Files removed: {files_deleted}"
                        )

                    if expired_tasks:
                        await session.commit()

            except Exception as e:
                logger.error(f"Error during expired DB-downloads cleanup: {e}")

            # Спим 15 минут
            await asyncio.sleep(900)

    async def clean_daily_trash(self) -> None:
        """
        Once a day, it cleans physical junk on the disk, based on the file age.
        """
        while True:
            # Сразу засыпаем на сутки (интервал раз в день)
            await asyncio.sleep(settings.app.timelife.one_day)

            try:
                logger.info("Running daily deep file-system trash cleanup...")
                now = time.time()

                if not self.downloads_dir.exists():
                    return None

                for f in os.listdir(self.downloads_dir):
                    file_path = self.downloads_dir / f

                    if os.path.isfile(file_path):
                        file_age = now - os.path.getmtime(file_path)

                        # Условия для удаления именно файлового МУСОРА:
                        # 1. Зависшие .part / .ytdl файлы старше 3 часов (загрузка упала/отменилась аварийно)
                        is_stuck_temp = f.endswith((".part", ".ytdl")) and file_age > (3 * 3600)

                        # 2. Любые сиротливые файлы (например .jpg обложки), которые лежат дольше суток
                        is_old_trash = file_age > settings.app.timelife.one_day

                        if is_stuck_temp or is_old_trash:
                            os.remove(file_path)
                            logger.info(
                                f"Daily cleanup physically removed trash file: {f} (Age: {int(file_age)}s)"
                            )
            except Exception as e:
                logger.error(f"Error during daily file trash cleanup: {e}")

    def _delete_files_by_task_id(self, task_id: str) -> bool:
        """
        Helper method for deleting all files on disk that start with task_id.
        """
        deleted_any: bool = False
        try:
            if not self.downloads_dir.exists():
                return deleted_any

            for f in os.listdir(self.downloads_dir):
                if f.startswith(task_id):
                    file_path = self.downloads_dir / f
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_any = True
        except Exception as e:
            logger.error(f"Failed to delete physical files for {task_id}: {e}")
        return deleted_any
