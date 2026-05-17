import os

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DownloadTask
from app.repositories import DownloadHistoryRepository
from app.schemas import FileData
from app.utils.delete_symbol import slugify_filename


class FriendlyFileNameService:
    """
    Service for generating user-friendly file names.
    """

    def __init__(
        self,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        Initialize the friendly file name service.
        """
        self.task_id = task_id
        self.repo = DownloadHistoryRepository(session)

    async def get_file_data(self) -> FileData:
        """
        Get file path and a sanitized friendly name.
        """
        history_item: DownloadTask | None = await self.repo.get_by_id(self.task_id)

        if not history_item or not history_item.file_path:
            raise HTTPException(status_code=404, detail="File not found")

        # Путь на диске - downloads/uuid.mkv
        file_disk_path: str = history_item.file_path

        if not os.path.exists(file_disk_path):
            raise HTTPException(status_code=404, detail="File physicaly missing")

        # Формируем красивое имя из title
        ext: str = os.path.splitext(file_disk_path)[1]
        friendly_name: str = f"{slugify_filename(history_item.title or 'video')}{ext}"

        return FileData(
            file_disk_path=file_disk_path,
            friendly_name=friendly_name,
        )
