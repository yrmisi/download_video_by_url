import json
import logging
from typing import Any, Sequence

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DownloadTask
from app.repositories import DownloadHistoryRepository

logger = logging.getLogger(__name__)


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
        Retrieve recent download history for a user using a single cache key per user.
        """
        # Ключ привязан к пользователю.
        cache_key: str = f"user_history:{user_id}"

        try:
            # 1. Пробуем взять всю закэшированную историю пользователя
            cached_data = await self.async_r.get(cache_key)
            if cached_data:
                logger.debug(f"Cache HIT for user history: {user_id}")
                raw_tasks: list[dict[str, Any]] = json.loads(cached_data)

                # Делаем пагинацию (срез) над массивом из кэша
                paginated_tasks: list[dict[str, Any]] = raw_tasks[offset : offset + limit]
                return [DownloadTask(**task) for task in paginated_tasks]

        except Exception as cache_err:
            # Если Redis недоступен, не падаем, логируем и идем напрямую в базу
            logger.warning(f"Redis history read error: {cache_err}")

        # 2. Если в кэше пусто (Cache MISS), запрашиваем из БД фиксированный топ (например, последние 100 записей)
        max_cache_size = 100
        logger.info(
            f"Cache MISS. Fetching top-{max_cache_size} history from DB for user: {user_id}"
        )

        full_history: Sequence[DownloadTask] = await self.repo.get_latest_by_user(
            user_id=user_id,
            limit=max_cache_size,
            offset=0,
        )

        # 3. Конвертируем полный список в словари для кэша
        full_history_list = [h.to_dict() for h in full_history if h is not None]

        if full_history_list:
            try:
                # Сохраняем весь пласт в один ключ на 10 минут
                await self.async_r.setex(cache_key, 600, json.dumps(full_history_list))
            except Exception as cache_err:
                logger.warning(f"Failed to write history to Redis cache: {cache_err}")

        # 4. Возвращаем клиенту срез для текущей страницы пагинации
        return full_history[offset : offset + limit]
