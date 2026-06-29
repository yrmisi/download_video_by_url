from typing import Annotated, Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .paths import ENVS_DIR


class StateConfig(BaseModel):
    """
    Configuration for task states.
    """

    finish: str = "finished"
    delete: str = "deleted"
    cancel: str = "cancelled"


class TimeLifeConfig(BaseModel):
    """
    Configuration for file lifetimes.
    """

    one_hour: int = 3600
    one_day: int = 86400


class AppConfig(BaseSettings):
    """
    Main application configuration.
    """

    state: StateConfig = StateConfig()
    timelife: TimeLifeConfig = TimeLifeConfig()
    windows_host_ip: Annotated[str | None, Field(alias="WINDOWS_HOST_IP")] = None
    base_url_yt: str = "https://www.youtube.com/watch?v={video_id}"

    model_config = SettingsConfigDict(
        env_file=ENVS_DIR / ".env.app-prod",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def proxy_url(self) -> str | None:
        """
        Generate a SOCKS5 proxy URL based on configuration.
        """
        # for developer in local
        # try:
        #     cmd = "ip route show | grep default | awk '{print $3}'"
        #     win_ip: str = subprocess.check_output(cmd, shell=True).decode().strip()
        #     return f"socks5://{win_ip}:1080"
        # except:
        #     return "socks5://127.0.0.1:1080"  # Фолбэк

        # for developer in docker
        # Берет чистый IP '172.17.16.1' из переменной окружения
        # если prod, то прокидывается None
        host_ip: str | None = self.windows_host_ip
        if host_ip:
            return f"socks5h://{host_ip}:1080"
        return None

    @property
    def base_ydl_opts(self) -> dict[str, Any]:
        """
        Get base yt-dlp options.
        """
        return {
            "proxy": self.proxy_url,
            "quiet": True,
            "nocheckcertificate": True,  # Игнорируем капризы SSL при handshake
            "socket_timeout": 15,  # Даем время VPN «проснуться»
            "retries": 5,  # Количество повторов при сбоях
            "legacy_server_connect": True,  # Фикс капризов старых/модифицированных TLS
            "youtube_include_hls_manifest": False,  # Запрещаем запрашивать m3u8 манифесты для инфы
            "extract_flat": (
                "in_playlist"
            ),  # извлекаем информацию в "плоском" режиме (быстрее и без лишних проверок)
        }

    @property
    def advanced_ydl_opts(self) -> dict[str, Any]:
        """
        Get base yt-dlp options.
        """
        return {
            "proxy": self.proxy_url,
            "outtmpl": "downloads/{task_id}.%(ext)s",
            "noplaylist": True,
            "writethumbnail": True,
            "no_color": True,  # Отключает ANSI-коды (цвета) в выводе
            # Сетевые настройки для стабильности через VPN:
            "nocheckcertificate": True,
            "socket_timeout": 15,
            "retries": 10,
            "fragment_retries": 10,  # Заставляем m3u8 не падать при обрывах
            "file_access_retries": 3,
            "postprocessors": [
                {"key": "EmbedThumbnail"},
                {"key": "FFmpegMetadata"},
            ],
            # Стандартная цветовая субдискретизация для ТВ
            "postprocessor_args": {
                "ffmpeg": [
                    "-pix_fmt",
                    "yuv420p",
                ],
            },
            "progress_hooks": [],
            "postprocessor_hooks": [],
        }
