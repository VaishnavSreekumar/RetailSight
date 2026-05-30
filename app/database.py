from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


class DatabaseSessionManager:
    """Manages async database engine and sessions."""

    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            echo=False,
        )
        self.session_maker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def close(self) -> None:
        """Closes connection pools and disposes of engine."""
        if self.engine is not None:
            await self.engine.dispose()

    async def check_connection(self) -> bool:
        """Runs a validation query to test connectivity."""
        try:
            async with self.session_maker() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


db_manager = DatabaseSessionManager(settings.DATABASE_URL)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator to retrieve active database session."""
    async with db_manager.session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
