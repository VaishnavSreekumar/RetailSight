from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    """Base service class wrapping transactional boundaries for business logic."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def commit(self) -> None:
        """Commits changes pending in the database session transaction."""
        await self.db_session.commit()

    async def rollback(self) -> None:
        """Rolls back changes pending in the database session transaction."""
        await self.db_session.rollback()
