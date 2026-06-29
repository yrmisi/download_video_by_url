from sqlalchemy import BigInteger, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DownloadTask(Base):
    """
    Database model representing a media download task.
    """

    __tablename__ = "download_history"

    url: Mapped[str] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    thumbnail: Mapped[str | None] = mapped_column(String, nullable=True)
    profile: Mapped[str] = mapped_column(String)
    quality: Mapped[str | None] = mapped_column(String, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    filesize: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")

    __table_args__ = (
        # Идеальный индекс для get_record_create_hour_ago()
        Index(
            "idx_download_history_status_created",  # Название индекса в БД
            "status",  # Первое поле (фильтрация)
            "created_at",  # Второе поле (сортировка)
        ),
    )

    def to_dict(self) -> dict[str, str | int | None]:
        """
        Convert model instance to dictionary representation.
        """

        return {
            "id": str(self.id),
            "url": self.url,
            "user_id": self.user_id,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "duration": self.duration,
            "resolution": self.resolution,
            "filesize": self.filesize,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
