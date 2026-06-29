from pydantic import BaseModel, ConfigDict
from uuid import UUID


class RecentHistoryResponse(BaseModel):
    """
    Response schema for download history.
    """

    id: UUID
    url: str
    title: str | None = None
    thumbnail: str | None = None
    duration: int | None = None
    resolution: str | None = None
    file_path: str | None = None
    filesize: int | None = None
    status: str

    # Добавляем конфиг для работы с объектами (если нужно будет мапить напрямую)
    model_config = ConfigDict(from_attributes=True)
