from typing import Sequence

from fastapi import APIRouter

from app.database.models import DownloadTask
from app.dependencies import AsyncRedisDep, AsyncSessionDep
from app.schemas import RecentHistoryResponse
from app.services import LatestLoadHistoryService

router = APIRouter()


@router.get(
    "/recent-history/{user_id}",
    response_model=list[RecentHistoryResponse],
)
async def get_recent_history(
    user_id: str,
    session: AsyncSessionDep,
    r: AsyncRedisDep,
) -> Sequence[DownloadTask]:
    """
    Endpoint to get recent download history for a user.
    """

    latest_history: LatestLoadHistoryService = LatestLoadHistoryService(session, r)
    history = await latest_history.get_history(user_id)
    return history
