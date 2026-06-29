import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.config.paths import DOWNLOADS_DIR
from app.database import session_pool
from app.database.models import DownloadTask
from app.repositories import DownloadHistoryRepository

logger = logging.getLogger(__name__)


class FileCleanupService:
    """
    Service for cleaning up expired and junk files with Graceful Shutdown support.
    """

    def __init__(
        self,
        session_pool: async_sessionmaker[AsyncSession] = session_pool,
        downloads_dir: Path = DOWNLOADS_DIR,
    ):
        """
        Initialize the file cleanup service.
        """
        self.session_pool = session_pool
        self.downloads_dir = downloads_dir

    async def clean_expired_downloads(self, shutdown_event: asyncio.Event) -> None:
        """
        Every 15 minutes, checks the database for files that expired within 1 hour
        of completion, deletes them from disk, and changes their status in the DB.
        """
        while not shutdown_event.is_set():
            try:
                logger.debug("Checking DB for downloads expired more than 1 hour ago...")

                async with self.session_pool() as session:
                    self.repo = DownloadHistoryRepository(session)
                    expired_tasks: Sequence[
                        DownloadTask
                    ] = await self.repo.get_record_create_hour_ago()

                    for task in expired_tasks:
                        # Если сигнал остановки пришел в процессе перебора,
                        # прерываемся, чтобы успеть закрыть приложение safely
                        if shutdown_event.is_set():
                            logger.warning("Cleanup aborted midway due to application shutdown.")
                            break

                        # Пытаемся удалить файлы по ID задачи
                        files_deleted = self._delete_files_by_task_id(str(task.id))

                        # Меняем статус в БД на 'deleted'
                        task.status = settings.app.state.delete
                        logger.info(
                            f"Task {task.id} expired. Status updated to 'deleted'. Files removed: {files_deleted}"
                        )

                    if expired_tasks and not shutdown_event.is_set():
                        await session.commit()

            except Exception as e:
                logger.error(f"Error during expired DB-downloads cleanup: {e}")

            # Спим 15 минут или до тех пор, пока не сработает shutdown_event
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=900.0)
                # Если пришли сюда без исключения — значит, взведен event.set(), выходим из цикла
                break
            except asyncio.TimeoutError:
                # Тайм-аут вышел, ивент не сработал — продолжаем крутить цикл
                continue

        logger.info("Expired files cleanup task exited cleanly.")

    async def clean_daily_trash(self, shutdown_event: asyncio.Event) -> None:
        """
        Once a day, cleans physical junk (.part, .ytdl, orphaned files) on the disk.
        """
        while not shutdown_event.is_set():
            # Сразу засыпаем на сутки (интервал раз в день) или до сигнала остановки
            try:
                await asyncio.wait_for(
                    shutdown_event.wait(), timeout=float(settings.app.timelife.one_day)
                )
                break  # Ивент сработал — завершаем таску
            except asyncio.TimeoutError:
                pass  # Сутки прошли — погнали чистить диск

            try:
                logger.info("Running daily deep file-system trash cleanup...")
                now = time.time()

                if not self.downloads_dir.exists():
                    continue

                for f in os.listdir(self.downloads_dir):
                    if shutdown_event.is_set():
                        break

                    file_path = self.downloads_dir / f

                    if os.path.isfile(file_path):
                        file_age = now - os.path.getmtime(file_path)

                        # 1. Зависшие .part / .ytdl файлы старше 3 часов
                        is_stuck_temp = f.endswith((".part", ".ytdl")) and file_age > (3 * 3600)

                        # 2. Любые сиротливые файлы (.jpg), которые лежат дольше суток
                        is_old_trash = file_age > settings.app.timelife.one_day

                        if is_stuck_temp or is_old_trash:
                            os.remove(file_path)
                            logger.info(
                                f"Daily cleanup physically removed trash file: {f} (Age: {int(file_age)}s)"
                            )
            except Exception as e:
                logger.error(f"Error during daily file trash cleanup: {e}")

        logger.info("Daily trash cleanup task exited cleanly.")

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
