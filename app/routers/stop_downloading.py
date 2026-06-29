from fastapi import APIRouter

from app.dependencies import AsyncRedisDep, AsyncSessionDep
from app.services import StoppedTaskServices

router = APIRouter()


@router.post("/cancel/{task_id}")
async def cancel_download(
    task_id: str,
    session: AsyncSessionDep,
    r: AsyncRedisDep,
) -> dict[str, str]:
    """
    Endpoint to cancel an ongoing download.
    """

    stopped_task: StoppedTaskServices = StoppedTaskServices(session, r)
    await stopped_task.stop_download(task_id)
    return {"status": "ok"}
