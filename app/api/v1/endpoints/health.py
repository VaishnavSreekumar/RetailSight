from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, db_manager
from app.models.event import Event

router = APIRouter()


class HealthResponse(BaseModel):
    """Schema representing system health check metrics."""

    status: str = Field(..., description="Overall status of the API instance.")
    database: str = Field(..., description="Database connectivity status.")
    environment: str = Field(..., description="Running deployment environment.")
    version: str = Field(..., description="App framework/platform version identifier.")
    last_event_timestamp: datetime | None = Field(
        None, description="ISO-8601 timestamp of the latest event."
    )
    stale_feed: bool = Field(
        False, description="Flag indicating if the last event is older than 10 minutes."
    )
    warning: str | None = Field(
        None, description="Warning messages, e.g. STALE_FEED warning if feed is stale."
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve system health status",
)
async def check_health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Checks database and event stream freshness status to verify health."""
    db_connected = await db_manager.check_connection()
    db_status = "connected" if db_connected else "disconnected"
    overall_status = "healthy" if db_connected else "unhealthy"

    last_event_timestamp = None
    stale_feed = False
    warning = None

    if db_connected:
        try:
            stmt = select(func.max(Event.timestamp))
            res = await db.execute(stmt)
            last_event_timestamp = res.scalar()
            if last_event_timestamp:
                if last_event_timestamp.tzinfo is None:
                    last_event_timestamp = last_event_timestamp.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                diff = now - last_event_timestamp
                if diff.total_seconds() > 600:  # 10 minutes
                    stale_feed = True
                    warning = "STALE_FEED"
        except Exception:
            # Fallback if query fails for any reason
            pass

    return HealthResponse(
        status=overall_status,
        database=db_status,
        environment=settings.APP_ENV,
        version="1.0.0",
        last_event_timestamp=last_event_timestamp,
        stale_feed=stale_feed,
        warning=warning,
    )
