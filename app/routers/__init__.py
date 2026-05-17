from .health import router as health_router
from .history import router as history_router
from .loading_media import router as load_media_router
from .media_info import router as media_info_router
from .stop_downloading import router as cancel_router
from .uploading_files import router as load_files_router

__all__ = [
    "load_media_router",
    "health_router",
    "history_router",
    "cancel_router",
    "media_info_router",
    "load_files_router",
]
