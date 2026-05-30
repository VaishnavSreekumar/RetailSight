from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.event_repository import EventRepository


@pytest.fixture(autouse=True)
def mock_db_operations(monkeypatch) -> None:
    """Mocks EventRepository insert and db commit methods for safe unit testing."""
    async def mock_insert(self, events):
        # Simulates successfully inserting all validated events
        return [event.id for event in events]

    monkeypatch.setattr(
        EventRepository, "insert_many_idempotent", mock_insert
    )
    monkeypatch.setattr(AsyncSession, "commit", AsyncMock())


@pytest.mark.asyncio
async def test_events_ingest_endpoint_success(client: AsyncClient) -> None:
    """Verifies that the /events/ingest endpoint validates schema and accepts valid batches."""
    payload = {
        "events": [
            {
                "store_id": "STORE_BLR_002",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_c8a2f1",
                "event_type": "ENTRY",
                "timestamp": "2026-05-30T09:44:24Z",
                "zone_id": "zone-entrance",
                "dwell_ms": 1500,
                "is_staff": False,
                "confidence": 0.98,
                "metadata": {"test": "val"},
            }
        ]
    }

    response = await client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers={"X-Trace-ID": "test-trace-id-123"},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["ingested_count"] == 1
    assert data["duplicate_count"] == 0
    assert data["failed_count"] == 0
    assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_events_ingest_invalid_identifiers(client: AsyncClient) -> None:
    """Verifies that the ingest endpoint records and reports invalid format identifiers."""
    payload = {
        "events": [
            {
                "store_id": "invalid-store",  # Must match STORE_[A-Z0-9_]+
                "camera_id": "invalid-cam",    # Must match CAM_[A-Z0-9_]+
                "visitor_id": "invalid-vis",  # Must match VIS_[a-zA-Z0-9_]+
                "event_type": "ENTRY",
                "timestamp": "2026-05-30T09:44:24Z",
            }
        ]
    }

    response = await client.post("/api/v1/events/ingest", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["ingested_count"] == 0
    assert data["failed_count"] == 1
    assert len(data["errors"]) > 0
    assert "validation failed" in data["errors"][0]


@pytest.mark.asyncio
async def test_events_ingest_invalid_enum(client: AsyncClient) -> None:
    """Verifies that the ingest endpoint records and reports invalid event types."""
    payload = {
        "events": [
            {
                "store_id": "STORE_BLR_002",
                "event_type": "INVALID_TYPE",  # Not in EventType Enum
                "timestamp": "2026-05-30T09:44:24Z",
            }
        ]
    }

    response = await client.post("/api/v1/events/ingest", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["ingested_count"] == 0
    assert data["failed_count"] == 1
    assert len(data["errors"]) > 0
    assert "validation failed" in data["errors"][0]
