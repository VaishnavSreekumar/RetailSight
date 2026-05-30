import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, enum.Enum):
    """Supported in-store retail event types."""

    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    REENTRY = "REENTRY"


class EventBase(BaseModel):
    """Base Event validation schema containing attributes shared across payloads."""

    store_id: str = Field(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="String identifier matching STORE_BLR_002 format.",
    )
    camera_id: str | None = Field(
        None,
        pattern=r"^CAM_[A-Z0-9_]+$",
        description="String identifier matching CAM_ENTRY_01 format.",
    )
    visitor_id: str | None = Field(
        None,
        pattern=r"^VIS_[a-zA-Z0-9_]+$",
        description="String identifier matching VIS_c8a2f1 format.",
    )
    event_type: EventType = Field(
        ..., description="Standard retail event classification."
    )
    timestamp: datetime = Field(
        ..., description="Date and time when the event was recorded."
    )
    zone_id: str | None = Field(
        None, max_length=100, description="Specific coordinate zone id in store."
    )
    dwell_ms: int | None = Field(
        None, ge=0, description="Duration in milliseconds spent inside the zone."
    )
    is_staff: bool = Field(
        False, description="Flag indicating if the subject is store staff."
    )
    confidence: float = Field(
        1.0, ge=0.0, le=1.0, description="Accuracy rating of detection event."
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Arbitrary custom schema payload parameters."
    )


class EventCreate(EventBase):
    """Validation schema for incoming single event ingestion requests."""

    # Clients can optionally provide a custom event_id to prevent duplicates
    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier to enforce transaction uniqueness.",
    )


class EventResponse(EventBase):
    """Validation schema representing ingested event records."""

    event_id: UUID = Field(..., description="Unique transaction ID of the event record.")

    model_config = ConfigDict(from_attributes=True)


class EventBatchIngestRequest(BaseModel):
    """Validation schema for batch event ingest payloads."""

    events: list[dict] = Field(
        ..., min_length=1, description="List of raw event payloads to process in batch."
    )


class EventBatchIngestResponse(BaseModel):
    """Validation schema reporting on batch ingest task execution status."""

    ingested_count: int = Field(
        ..., description="Total count of successfully created records."
    )
    duplicate_count: int = Field(
        ..., description="Total count of skipped duplicate event records."
    )
    failed_count: int = Field(
        ..., description="Total count of records failing schema checks."
    )
    errors: list[str] = Field(
        ..., description="Description list of validation errors encountered."
    )
