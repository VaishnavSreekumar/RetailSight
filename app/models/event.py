from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.schemas.event import EventType


class Event(Base):
    """SQLAlchemy model representing a tracking event from in-store cameras."""

    # Override id attribute mapping it to the 'event_id' database column
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        name="event_id",
        primary_key=True,
        default=uuid4,
        index=True,
    )
    # Refactored store_id, camera_id and visitor_id to strings matching challenge schema
    store_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    camera_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    visitor_id: Mapped[str | None] = mapped_column(
        String(50), index=True, nullable=True
    )
    # Event type linked to PostgreSQL native enum schema mapping
    event_type: Mapped[EventType] = mapped_column(
        SQLEnum(EventType), index=True, nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    zone_id: Mapped[str | None] = mapped_column(
        String(100), index=True, nullable=True
    )
    dwell_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_staff: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )

    # Avoids collision with Base.metadata property using explicit name parameter mapping
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
