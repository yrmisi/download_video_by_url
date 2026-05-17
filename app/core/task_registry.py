import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services import DownloadTaskService

active_tasks: dict[str, asyncio.Task] = {}


async def running_task(task_id: str, download_task: DownloadTaskService) -> None:
    """ """
    # Создаем asyncio задачу вручную
    loop_task = asyncio.create_task(download_task.run_download())
    # Сохраняем её в реестр
    active_tasks[task_id] = loop_task
    # Удаляем из реестра, когда она завершится (успешно или с ошибкой)
    loop_task.add_done_callback(lambda t: active_tasks.pop(task_id, None))
