import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services import DownloadTaskService

active_tasks: dict[str, asyncio.Task[None]] = {}
# Разрешаем серверу качать максимум 3 видео одновременно во всем приложении
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(3)


async def running_task(task_id: str, download_task: DownloadTaskService) -> None:
    """ """
    async with DOWNLOAD_SEMAPHORE:
        # Создаем asyncio задачу вручную
        loop_task = asyncio.create_task(download_task.run_download())
        # Сохраняем её в реестр
        active_tasks[task_id] = loop_task
        # Удаляем из реестра, когда она завершится (успешно или с ошибкой)
        loop_task.add_done_callback(lambda t: active_tasks.pop(task_id, None))
