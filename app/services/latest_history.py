import json
from typing import Any, Sequence

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
        async_redis_client: Redis,
    ) -> None:
        """
        Initialize the latest history service.
        """

        self.repo = DownloadHistoryRepository(session)
        self.async_r = async_redis_client

    async def get_history(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> Sequence[DownloadTask]:
        """
        Retrieve recent download history for a user.
        """

        # Ключ теперь уникален для каждой комбинации страницы
        cache_key: str = f"user_history:{user_id}:l:{limit}:o:{offset}"

        # Пробуем взять из кэша
        cached_data = await self.async_r.get(cache_key)
        if cached_data:
            # Превращаем сохраненные словари обратно в ORM-модели
            raw_tasks: list[dict[str, Any]] = json.loads(cached_data)
            return [DownloadTask(**task) for task in raw_tasks]

        # Если в кэше пусто, идем в базу с параметрами пагинации
        history: Sequence[DownloadTask] = await self.repo.get_latest_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        # Конвертируем модели в словари для JSON
        history_list = [h.to_dict() for h in history if h is not None]

        # Сохраняем в кэш на 5-10 минут (чтобы не забивать память вечно)
        await self.async_r.setex(cache_key, 600, json.dumps(history_list))

        return history
