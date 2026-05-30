from typing import Sequence
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    """Repository handling data access logic for Event models."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Event, db_session)

    async def insert_many_idempotent(self, events: Sequence[Event]) -> list[UUID]:
        """Inserts events in batch using postgres ON CONFLICT DO NOTHING.

        Returns a list of successfully inserted Event UUID primary keys.
        """
        if not events:
            return []

        # Prepare raw values for dialect-specific insert statements
        values_list = [
            {
                "event_id": event.id,
                "store_id": event.store_id,
                "camera_id": event.camera_id,
                "visitor_id": event.visitor_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "zone_id": event.zone_id,
                "dwell_ms": event.dwell_ms,
                "is_staff": event.is_staff,
                "confidence": event.confidence,
                "metadata": event.event_metadata,
            }
            for event in events
        ]

        stmt = insert(Event.__table__).values(values_list)
        # Apply postgres conflict safety DO NOTHING on index event_id
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["event_id"]
        ).returning(Event.__table__.c.event_id)

        result = await self.db_session.execute(stmt)
        inserted_ids = result.scalars().all()
        
        return list(inserted_ids)
