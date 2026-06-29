import asyncio
import hashlib
import json
import logging
from dataclasses import asdict
from typing import Any, Mapping

from redis.asyncio import Redis

from app.config import settings
from app.core.ytdlp.executor import get_raw_extract_info
from app.schemas import MediaInfo

logger = logging.getLogger(__name__)


class MediaInfoService:
    def __init__(self, async_redis_client: Redis) -> None:
        self.async_r = async_redis_client

    async def get_media_info(self, url: str) -> MediaInfo:
        """
        Retrieve basic metadata for a given URL with Redis caching.
        """
        # 1. Считаем хэш от URL для ключа в Redis
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        cache_key = f"extract_info:{url_hash}"

        try:
            # 2. Проверяем кэш
            cached_data = await self.async_r.get(cache_key)
            if cached_data:
                logger.info(f"Cache HIT for URL hash: {url_hash}")
                data_dict = json.loads(cached_data)
                return MediaInfo(**data_dict)
        except Exception as cache_err:
            # Если Redis упал, не ломаем приложение, просто логируем и идем в сеть
            logger.warning(f"Redis cache error: {cache_err}")

        # 3. Кэша нет -> Идем в сеть через пул потоков, чтобы не блокировать FastAPI
        logger.info(f"Cache MISS. Fetching metadata via yt-dlp for hash: {url_hash}")
        loop = asyncio.get_running_loop()

        info: Mapping[str, Any] = await loop.run_in_executor(
            None,
            get_raw_extract_info,
            url,
            settings.app.base_ydl_opts,
            False,
        )

        media_info: MediaInfo = MediaInfo(
            title=info.get("title") or "Unknown",
            thumbnail=info.get("thumbnail") or "",
            max_quality=info.get("height") or 1080,
        )

        # 4. Сохраняем собранную модель в кэш на 1 час (3600 секунд)
        try:
            await self.async_r.setex(cache_key, 3600, json.dumps(asdict(media_info)))
        except Exception as cache_err:
            logger.warning(f"Failed to write to Redis cache: {cache_err}")

        return media_info
