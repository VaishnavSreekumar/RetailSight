
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brigade_transaction import BrigadeTransaction
from app.repositories.base import BaseRepository

class BrigadeTransactionRepository(BaseRepository):
    def __init__(self, db_session: AsyncSession):
        super().__init__(BrigadeTransaction, db_session)

    async def get_total_revenue_in_range(self, start_time: datetime, end_time: datetime, revenue_col: str = "nmv") -> float:
        """
        Calculates total revenue (using NMV by default) within a given time range.
        """
        stmt = select(func.sum(getattr(BrigadeTransaction, revenue_col))).where(
            BrigadeTransaction.order_date.between(start_time.date(), end_time.date())
        )
        result = await self.db_session.execute(stmt)
        total_revenue = result.scalar_one_or_none()
        return total_revenue or 0.0

    async def get_revenue_by_hour(self, start_time: datetime, end_time: datetime, revenue_col: str = "nmv"):
        stmt = select(
            func.extract('hour', BrigadeTransaction.order_time).label('hour'),
            func.sum(getattr(BrigadeTransaction, revenue_col)).label('revenue')
        ).where(
            BrigadeTransaction.order_date.between(start_time.date(), end_time.date())
        ).group_by('hour').order_by('hour')
        result = await self.db_session.execute(stmt)
        return result.all()

    async def get_top_products(self, start_time: datetime, end_time: datetime, limit: int = 5):
        stmt = select(
            BrigadeTransaction.product_name,
            func.sum(BrigadeTransaction.qty).label('total_quantity')
        ).where(
            BrigadeTransaction.order_date.between(start_time.date(), end_time.date())
        ).group_by(BrigadeTransaction.product_name).order_by(func.sum(BrigadeTransaction.qty).desc()).limit(limit)
        result = await self.db_session.execute(stmt)
        return result.all()
