from datetime import datetime
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visitor_session import VisitorSession
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[VisitorSession]):
    """Repository handling data access logic for VisitorSession models."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(VisitorSession, db_session)

    async def get_by_store_and_timerange(
        self,
        store_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Sequence[VisitorSession]:
        """Retrieves sessions for a store, filtered by an optional time window."""
        stmt = select(self.model).filter(self.model.store_id == store_id)
        if start_time is not None:
            stmt = stmt.filter(self.model.entered_at >= start_time)
        if end_time is not None:
            stmt = stmt.filter(self.model.entered_at <= end_time)
        result = await self.db_session.execute(stmt)
        return result.scalars().all()

    async def get_by_store(self, store_id: str) -> Sequence[VisitorSession]:
        """Retrieves all sessions associated with a store."""
        return await self.get_by_store_and_timerange(store_id)

    async def delete_by_store(self, store_id: str) -> None:
        """Deletes all sessions associated with a store."""
        from sqlalchemy import delete
        stmt = delete(self.model).filter(self.model.store_id == store_id)
        await self.db_session.execute(stmt)

