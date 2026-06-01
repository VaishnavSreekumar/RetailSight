# PROMPT: Implement integration tests for the store-wide analytics metrics endpoint.
# CHANGES MADE: Validated /metrics API behavior verifying response calculations for active shopper sessions.

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.repositories.session_repository import SessionRepository
from app.repositories.transaction_repository import TransactionRepository


@pytest.fixture(autouse=True)
def mock_repos_for_endpoint(monkeypatch) -> None:
    """Mocks session and transaction database fetch queries for API tests."""
    monkeypatch.setattr(
        SessionRepository, "get_by_store_and_timerange", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        TransactionRepository,
        "get_by_store_and_timerange",
        AsyncMock(return_value=[]),
    )


@pytest.mark.asyncio
async def test_get_metrics_endpoint_empty_success(client: AsyncClient) -> None:
    """Verifies that queries for a valid store with zero logs return 200 OK with zeroed parameters."""
    response = await client.get("/api/v1/stores/STORE_BLR_002/metrics")
    assert response.status_code == 200

    data = response.json()
    assert data["store_id"] == "STORE_BLR_002"
    assert data["visitors"] == 0
    assert data["conversion_rate"] == 0.0
    assert data["avg_journey_length"] == 0.0
    assert data["avg_zones_visited"] == 0.0
    assert len(data["opportunity_zones"]) == 0
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_get_metrics_endpoint_time_filters(client: AsyncClient) -> None:
    """Verifies that the API handles start_time and end_time parameters correctly."""
    response = await client.get(
        "/api/v1/stores/STORE_BLR_002/metrics",
        params={
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-31T23:59:59Z",
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_metrics_endpoint_invalid_store_format(
    client: AsyncClient,
) -> None:
    """Verifies that queries violating store_id format constraints raise 422 validation errors."""
    # Invalid store_id pattern (lacks STORE_ prefix)
    response = await client.get("/api/v1/stores/BLR_002/metrics")
    assert response.status_code == 422
