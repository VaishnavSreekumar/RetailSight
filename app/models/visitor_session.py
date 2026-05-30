from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VisitorSession(Base):
    """SQLAlchemy model representing a tracking session of an in-store visitor."""

    # Override id to map to database column 'session_id'
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        name="session_id",
        primary_key=True,
        default=uuid4,
        index=True,
    )
    visitor_id: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )
    store_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    exited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Extended analytics journey attributes
    journey_path: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    zone_dwell_times: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    zone_transitions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_staff: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    has_converted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    has_joined_billing_queue: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    associated_txn_id: Mapped[str | None] = mapped_column(
        String(100), index=True, nullable=True
    )
    intent_score: Mapped[float | None] = mapped_column(Float, nullable=True)
