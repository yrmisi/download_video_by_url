import asyncio
import json
import logging
import os
from functools import partial
from pathlib import Path
from typing import Any, Mapping

from redis import Redis

from app.config import settings
from app.config.paths import DOWNLOADS_DIR
from app.core.ytdlp.callbacks import postprocessor_hook, progress_hook
from app.core.ytdlp.executor import execute_ydl
from app.repositories import DownloadHistoryRepository
from app.schemas import (
    DownloadHistoryItems,
    DownloadProfile,
    LoadMediaRequest,
    UpdateLoadHistoryItems,
)

logger = logging.getLogger(__name__)


class DownloadTaskService:
    """
    Service for handling video download tasks.
    """

    def __init__(
        self,
        task_id: str,
        session_pool,
        load_media: LoadMediaRequest,
        redis: Redis,
    ) -> None:
        """
        Initialize the download task service.
        """
        self.task_id = task_id
        self.session_pool = session_pool
        self.load_media = load_media
        self.r = redis

    async def run_download(self) -> None:
        """
        Execute the media download process.
        """
        # Создаем "заряженные" хуки с уже подставленными task_id и redis
        p_hook = partial(progress_hook, task_id=self.task_id, redis_client=self.r)
        pp_hook = partial(postprocessor_hook, task_id=self.task_id, redis_client=self.r)

        ydl_opts = settings.app.advanced_ydl_opts

        ydl_opts["outtmpl"] = ydl_opts["outtmpl"].format(task_id=self.task_id)
        ydl_opts["progress_hooks"].append(p_hook)
        ydl_opts["postprocessor_hooks"].append(pp_hook)

        self._set_ydl_opts(ydl_opts)

        item = DownloadHistoryItems(
            id=self.task_id,
            url=str(self.load_media.url),
            user_id=self.load_media.user_id or "unknown",
            profile=self.load_media.profile,
            quality=self.load_media.quality or "default",
        )
        async with self.session_pool() as session:
            self.repo = DownloadHistoryRepository(session)
            await self.repo.create(item)

        try:
            # 2. ЗАПУСКАЕМ ТОЛЬКО ОДИН РАЗ
            # info — словарь с данными, path — ожидаемый путь файла
            loop = asyncio.get_running_loop()
            info, path = await loop.run_in_executor(
                None,
                execute_ydl,
                ydl_opts,
                str(self.load_media.url),
            )
        except asyncio.CancelledError:
            logger.info(f"Task {self.task_id} was cancelled!")
            self.r.set(f"task:{self.task_id}", json.dumps({"status": "cancelled"}))
            raise

        # 3. ПОИСК ФАЙЛА (так как расширение могло измениться после FFmpeg)
        actual_filename: str = self._check_file_for_location(path, DOWNLOADS_DIR)

        # 4. Отправляем в Redis финальный статус и ССЫЛКУ url
        final_data = {
            "status": settings.app.state.finish,
            "percent": "100%",
            "file_url": f"/api/files/{self.task_id}",
        }
        self.r.setex(
            f"task:{self.task_id}",
            3600,
            json.dumps(final_data),
        )
        item_update = UpdateLoadHistoryItems(
            title=info.get("title") or "unknown",
            thumbnail=info.get("thumbnail") or "unknown",
            duration=info.get("duration") or 0,  # в секундах
            resolution=self._resolution_label(info),
            file_path=f"downloads/{actual_filename}",
            filesize=self._filesize_label(
                DOWNLOADS_DIR.joinpath(actual_filename).as_posix(),
                info,
            ),
            status=settings.app.state.finish,
        )
        async with self.session_pool() as session:
            self.repo = DownloadHistoryRepository(session)
            await self.repo.update(
                self.task_id,
                item_update,
            )
        # Удаляем кэш истории пользователя, чтобы при следующем заходе он обновился
        self.r.delete(f"user_history:{self.load_media.user_id}")

        logger.info(
            f"Task {self.task_id} finished, cache invalidated for user {self.load_media.user_id}"
        )

    def _set_ydl_opts(self, opts: Any) -> None:
        """Configure yt-dlp options based on the profile."""
        if self.load_media.profile == DownloadProfile.pc_tv:
            # НОВЫЕ ТВ / ПК: Тянем лучшее (VP9/AV1), плееры на ПК прочитают всё
            # Позволяет получить 4K и HDR, если они есть
            opts["format"] = f"bestvideo[height<={self.load_media.quality}]+bestaudio/best"
            opts["merge_output_format"] = "mkv"  # MKV лучше держит современные кодеки

        elif self.load_media.profile == DownloadProfile.legacy_tv:
            # СТАРЫЕ ТВ: Только H.264 (avc1), только MP4, звук AAC
            opts["format"] = (
                f"bestvideo[height<={self.load_media.quality}][vcodec^=avc1]+"
                f"bestaudio[ext=m4a]/best[height<={self.load_media.quality}][vcodec^=avc1]"
            )
            opts["merge_output_format"] = "mp4"

        elif self.load_media.profile == DownloadProfile.mobile:
            # СМАРТФОНЫ: Принудительно 720p (для экономии места) и MP4
            opts["format"] = "best[ext=mp4][height<=720]/best"
            opts["merge_output_format"] = "mp4"

        elif self.load_media.profile == DownloadProfile.mp4:
            # Качаем сразу готовый файл до 1080p
            opts["format"] = "best[ext=mp4]"

        elif self.load_media.profile == DownloadProfile.audio:
            opts["format"] = "bestaudio/best"
            # Добавляем конвертацию в mp3 в начало списка постпроцессоров
            opts["postprocessors"].insert(
                0,
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                },
            )

    @staticmethod
    def _check_file_for_location(
        target_path: str,
        downloads_dir: Path,
    ) -> str:
        """
        Checks for the presence of a file. If the extension has changed (for example, from ffmpeg), searches for the file by its base name (task_id) in the specified directory.
        """
        filename = os.path.basename(target_path)

        # 1. Проверяем точный путь, который вернул yt-dlp
        if os.path.exists(target_path):
            return filename

        # 2. Если не найден, ищем в папке downloads по task_id
        name_without_ext = os.path.splitext(filename)[0]

        try:
            for f in os.listdir(downloads_dir):
                # Исключаем временные файлы .part и .ytdl
                if f.startswith(name_without_ext) and not f.endswith(('.part', '.ytdl')):
                    return f
        except FileNotFoundError:
            logger.error(f"Directory not found: {downloads_dir}")

        return filename

    @staticmethod
    def _resolution_label(info: Mapping[str, Any]) -> str:
        """
        Extract resolution label from info dict.
        """
        height: int | None = info.get("height")
        return f"{height}p" if height else (info.get("format_note") or "Unknown")

    @staticmethod
    def _filesize_label(
        full_path: str,
        info: Mapping[str, Any],
    ) -> int:
        """
        Determine the file size from disk or info dict.
        """
        physical_size: int = 0
        if os.path.exists(full_path):
            physical_size = os.path.getsize(full_path)
        return physical_size or info.get("filesize") or info.get("filesize_approx") or 0
