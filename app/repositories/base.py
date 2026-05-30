from typing import Generic, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.base import Base

# Type variable bound to our Declarative Base class
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic CRUD repository interface wrapper for SQLAlchemy 2.0 Async."""

    def __init__(self, model: Type[ModelType], db_session: AsyncSession):
        self.model = model
        self.db_session = db_session

    async def get(self, obj_id: UUID) -> ModelType | None:
        """Retrieves a single model record by its primary key ID."""
        result = await self.db_session.execute(
            select(self.model).filter(self.model.id == obj_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Retrieves all model records matching pagination constraints."""
        result = await self.db_session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, obj_in: ModelType) -> ModelType:
        """Persists a new model record instance in the database session."""
        self.db_session.add(obj_in)
        await self.db_session.flush()
        await self.db_session.refresh(obj_in)
        return obj_in

    async def update(self, db_obj: ModelType, update_data: dict) -> ModelType:
        """Updates attributes of an existing model record instance."""
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db_session.add(db_obj)
        await self.db_session.flush()
        await self.db_session.refresh(db_obj)
        return db_obj

    async def delete(self, obj_id: UUID) -> ModelType | None:
        """Deletes a database model record instance by its ID."""
        obj = await self.get(obj_id)
        if obj is not None:
            await self.db_session.delete(obj)
            await self.db_session.flush()
        return obj
