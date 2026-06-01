# PROMPT: Create endpoint test suite for operational anomaly detection API.
# CHANGES MADE: Implemented mock-based validation for /anomalies GET endpoint verifying empty state responses.

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.repositories.session_repository import SessionRepository


@pytest.fixture(autouse=True)
def mock_repos_for_anomalies(monkeypatch) -> None:
    """Mocks session database fetch queries for API anomalies tests."""
    monkeypatch.setattr(
        SessionRepository, "get_by_store_and_timerange", AsyncMock(return_value=[])
    )


@pytest.mark.asyncio
async def test_get_anomalies_endpoint_empty_success(client: AsyncClient) -> None:
    """Verifies that queries for a valid store with zero sessions return 200 OK with empty anomalies list."""
    response = await client.get("/api/v1/stores/STORE_BLR_002/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_anomalies_endpoint_time_filters(client: AsyncClient) -> None:
    """Verifies that the anomalies API handles start_time and end_time parameters correctly."""
    response = await client.get(
        "/api/v1/stores/STORE_BLR_002/anomalies",
        params={
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-31T23:59:59Z",
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_anomalies_endpoint_invalid_store_format(
    client: AsyncClient,
) -> None:
    """Verifies that queries violating store_id format constraints raise 422 validation errors."""
    # Invalid store_id pattern (lacks STORE_ prefix)
    response = await client.get("/api/v1/stores/BLR_002/anomalies")
    assert response.status_code == 422
