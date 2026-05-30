from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Transaction(Base):
    """SQLAlchemy model representing a checkout transaction at the point of sale."""

    # Override id to map to database column 'transaction_id'
    id: Mapped[str] = mapped_column(
        String(100),
        name="transaction_id",
        primary_key=True,
        index=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("visitor_session.session_id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    store_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # List of purchased items containing quantity, price, SKU/ID details
    items: Mapped[list | None] = mapped_column(JSONB, nullable=True)
