from datetime import datetime
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Repository handling data access logic for Transaction models."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Transaction, db_session)

    async def get_by_store_and_timerange(
        self,
        store_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Sequence[Transaction]:
        """Retrieves transactions for a store, filtered by an optional time window."""
        stmt = select(self.model).filter(self.model.store_id == store_id)
        if start_time is not None:
            stmt = stmt.filter(self.model.timestamp >= start_time)
        if end_time is not None:
            stmt = stmt.filter(self.model.timestamp <= end_time)
        result = await self.db_session.execute(stmt)
        return result.scalars().all()

    async def get_by_store(self, store_id: str) -> Sequence[Transaction]:
        """Retrieves all transactions associated with a store."""
        return await self.get_by_store_and_timerange(store_id)

    async def clear_session_links_for_store(self, store_id: str) -> None:
        """Clears all session foreign key associations for transactions in a store."""
        from sqlalchemy import update
        stmt = (
            update(self.model)
            .filter(self.model.store_id == store_id)
            .values(session_id=None)
        )
        await self.db_session.execute(stmt)

