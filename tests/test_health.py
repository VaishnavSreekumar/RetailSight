# PROMPT: Create system health status endpoint verification checks.
# CHANGES MADE: Added test assertions validating database connectivity status, last event timestamp, and STALE_FEED warning logic.

import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.schemas.event import EventType


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """Verifies that the system health status API reports correctly."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["database"] == "connected"
    assert "environment" in payload
    assert "version" in payload
    assert payload["last_event_timestamp"] is None
    assert payload["stale_feed"] is False
    assert payload["warning"] is None


@pytest.mark.asyncio
async def test_health_endpoint_stale_feed(client: AsyncClient, test_db: AsyncSession) -> None:
    """Verifies health API behavior with fresh and stale event feeds."""
    # 1. Insert a fresh event
    now = datetime.now(timezone.utc)
    fresh_event = Event(
        store_id="STORE_BLR_002",
        camera_id="CAM_ENTRY_01",
        visitor_id="VIS_001",
        event_type=EventType.ENTRY,
        timestamp=now - timedelta(minutes=2),  # 2 minutes ago (fresh)
        confidence=0.95,
        is_staff=False,
    )
    test_db.add(fresh_event)
    await test_db.commit()

    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["stale_feed"] is False
    assert payload["warning"] is None
    assert payload["last_event_timestamp"] is not None

    # 2. Insert a stale event and delete the fresh one to make it stale
    await test_db.delete(fresh_event)
    stale_event = Event(
        store_id="STORE_BLR_002",
        camera_id="CAM_ENTRY_01",
        visitor_id="VIS_002",
        event_type=EventType.ENTRY,
        timestamp=now - timedelta(minutes=15),  # 15 minutes ago (stale)
        confidence=0.95,
        is_staff=False,
    )
    test_db.add(stale_event)
    await test_db.commit()

    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["stale_feed"] is True
    assert payload["warning"] == "STALE_FEED"

    # Cleanup
    await test_db.delete(stale_event)
    await test_db.commit()
