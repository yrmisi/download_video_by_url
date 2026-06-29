from typing import Sequence

from fastapi import APIRouter, Query

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
    async_r: AsyncRedisDep,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Sequence[DownloadTask]:
    """
    Endpoint to get recent download history for a user.
    """

    service: LatestLoadHistoryService = LatestLoadHistoryService(session, async_r)
    latest_history: Sequence[DownloadTask] = await service.get_history(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return latest_history
