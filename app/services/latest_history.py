import json
from typing import Sequence

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DownloadTask
from app.repositories import DownloadHistoryRepository


class LatestLoadHistoryService:
    """
    Service for retrieving user download history.
    """

    def __init__(
        self,
        session: AsyncSession,
        r: Redis,
    ) -> None:
        """
        Initialize the latest history service.
        """

        self.repo = DownloadHistoryRepository(session)
        self.r = r

    async def get_history(self, user_id: str) -> Sequence[DownloadTask]:
        """
        Retrieve recent download history for a user.
        """

        cache_key: str = f"user_history:{user_id}"

        # 1. Пробуем взять из кэша
        cached_data = await self.r.get(cache_key)
        if cached_data:
            return [DownloadTask(**task) for task in json.loads(cached_data)]

        # 2. Если в кэше пусто, идем в базу
        history: Sequence[DownloadTask] = await self.repo.get_latest_by_user(
            user_id=user_id,
        )

        # Конвертируем модели в словари для JSON
        history_list = [h.to_dict() for h in history if h is not None]

        # 3. Сохраняем в кэш на 5-10 минут (чтобы не забивать память вечно)
        await self.r.setex(cache_key, 600, json.dumps(history_list))

        return history
