from fastapi import APIRouter, Depends, Header, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.event import Event
from app.repositories.event_repository import EventRepository
from app.schemas.event import (
    EventBatchIngestRequest,
    EventBatchIngestResponse,
    EventCreate,
)

router = APIRouter()


@router.post(
    "/ingest",
    response_model=EventBatchIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of retail camera detection events",
)
async def ingest_events(
    payload: EventBatchIngestRequest,
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
) -> EventBatchIngestResponse:
    """Validates and ingests batch events into the database store.

    Performs item-level schema validation. Accepts an optional
    X-Idempotency-Key header to track request retry safety.
    """
    event_repo = EventRepository(db)

    valid_events = []
    errors = []
    failed_count = 0

    # Parse and validate events individually to report failed records
    for idx, raw_event in enumerate(payload.events):
        try:
            event_data = EventCreate.model_validate(raw_event)
            valid_events.append(event_data)
        except ValidationError as err:
            failed_count += 1
            errors.append(f"Event at index {idx} validation failed: {str(err)}")
        except Exception as exc:
            failed_count += 1
            errors.append(
                f"Event at index {idx} failed with unexpected error: {str(exc)}"
            )

    # Map successfully validated events to database Event model
    db_events = [
        Event(
            id=item.event_id,
            store_id=item.store_id,
            camera_id=item.camera_id,
            visitor_id=item.visitor_id,
            event_type=item.event_type,
            timestamp=item.timestamp,
            zone_id=item.zone_id,
            dwell_ms=item.dwell_ms,
            is_staff=item.is_staff,
            confidence=item.confidence,
            event_metadata=item.metadata,
        )
        for item in valid_events
    ]

    ingested_ids = []
    if db_events:
        # Run postgres native insert statement with on_conflict_do_nothing
        ingested_ids = await event_repo.insert_many_idempotent(db_events)
        await db.commit()

    ingested_count = len(ingested_ids)
    duplicate_count = len(db_events) - ingested_count

    return EventBatchIngestResponse(
        ingested_count=ingested_count,
        duplicate_count=duplicate_count,
        failed_count=failed_count,
        errors=errors,
    )
