from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.transaction import Transaction
from app.repositories.event_repository import EventRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.session_hydration_service import SessionHydrationService
from app.schemas.event import EventType


@pytest.mark.asyncio
async def test_session_hydration_and_linking(client: AsyncClient, monkeypatch) -> None:
    """Verifies that the /stores/{store_id}/hydrate endpoint runs correctly."""
    store_id = "STORE_BLR_002"
    
    async def mock_hydrate(self, store):
        return {"hydrated_count": 2, "linked_count": 1}

    monkeypatch.setattr(SessionHydrationService, "hydrate_store_sessions", mock_hydrate)

    response = await client.post(f"/api/v1/stores/{store_id}/hydrate")
    assert response.status_code == 200
    data = response.json()
    assert data["hydrated_count"] == 2
    assert data["linked_count"] == 1


@pytest.mark.asyncio
async def test_session_hydration_service_direct(monkeypatch) -> None:
    """Directly tests the SessionHydrationService with mocked repository interactions."""
    event_repo = EventRepository(AsyncSession)
    session_repo = SessionRepository(AsyncSession)
    txn_repo = TransactionRepository(AsyncSession)

    store_id = "STORE_BLR_002"

    mock_events = [
        Event(
            id="e0000000-0000-0000-0000-000000000001",
            store_id=store_id,
            visitor_id="VIS_001",
            event_type=EventType.ENTRY,
            timestamp=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            confidence=0.95,
        ),
        Event(
            id="e0000000-0000-0000-0000-000000000002",
            store_id=store_id,
            visitor_id="VIS_001",
            event_type=EventType.BILLING_QUEUE_JOIN,
            timestamp=datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc),
            confidence=0.92,
        ),
        Event(
            id="e0000000-0000-0000-0000-000000000003",
            store_id=store_id,
            visitor_id="VIS_001",
            event_type=EventType.EXIT,
            timestamp=datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
            confidence=0.96,
        )
    ]

    mock_txns = [
        Transaction(
            id="txn_001",
            store_id=store_id,
            timestamp=datetime(2026, 5, 30, 10, 8, 0, tzinfo=timezone.utc),
            total_amount=150.00,
            session_id=None,
        )
    ]

    async def mock_execute_events(stmt):
        class MockResult:
            def scalars(self):
                class MockScalars:
                    def all(self):
                        return mock_events
                return MockScalars()
        return MockResult()

    async def mock_get_txns(store):
        return mock_txns

    async def mock_async_none(*args, **kwargs):
        return None

    monkeypatch.setattr(event_repo.db_session, "execute", mock_execute_events)
    monkeypatch.setattr(session_repo, "delete_by_store", mock_async_none)
    monkeypatch.setattr(txn_repo, "clear_session_links_for_store", mock_async_none)
    monkeypatch.setattr(txn_repo, "get_by_store", mock_get_txns)
    
    # Mock database session operations
    session_repo.db_session.add = lambda x: None
    monkeypatch.setattr(session_repo.db_session, "commit", mock_async_none)
    monkeypatch.setattr(session_repo.db_session, "flush", mock_async_none)

    service = SessionHydrationService(event_repo, session_repo, txn_repo)
    result = await service.hydrate_store_sessions(store_id)

    assert result["hydrated_count"] == 1
    assert result["linked_count"] == 1
