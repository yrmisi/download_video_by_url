from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_resilience import retry_db_transaction
from app.database.models import DownloadTask
from app.schemas import DownloadHistoryItems, UpdateLoadHistoryItems


class DownloadHistoryRepository:
    """
    Repository for managing download history database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @retry_db_transaction
    async def create(self, items: DownloadHistoryItems) -> None:
        instance = DownloadTask(**asdict(items))
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)

    @retry_db_transaction
    async def update(
        self,
        task_id: str,
        items_update: UpdateLoadHistoryItems,
    ) -> None:
        stmt = update(DownloadTask).where(DownloadTask.id == task_id).values(**asdict(items_update))
        await self.session.execute(stmt)
        await self.session.commit()

    @retry_db_transaction
    async def get_by_id(self, task_id: str) -> DownloadTask | None:
        return await self.session.get(DownloadTask, task_id)

    @retry_db_transaction
    async def get_latest_by_user(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> Sequence[DownloadTask]:
        result = await self.session.execute(
            select(DownloadTask)
            .where(
                DownloadTask.user_id == user_id,
                or_(
                    DownloadTask.status == "finished",
                    DownloadTask.status == "deleted",
                ),
            )
            .order_by(DownloadTask.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @retry_db_transaction
    async def get_record_create_hour_ago(self, hours: int = 1) -> Sequence[DownloadTask]:
        """
        Retrieve finished downloads completed more than specified hours ago.
        """

        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = select(DownloadTask).where(
            DownloadTask.status == "finished",
            DownloadTask.created_at < time_threshold,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    @retry_db_transaction
    async def save(self, task: DownloadTask) -> None:
        """
        Safe commit for task instance changes with automatic retry on transient DB errors.
        """

        self.session.add(task)
        await self.session.commit()
