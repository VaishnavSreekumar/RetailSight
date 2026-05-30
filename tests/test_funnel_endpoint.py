from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.repositories.session_repository import SessionRepository


@pytest.fixture(autouse=True)
def mock_repos_for_funnel(monkeypatch) -> None:
    """Mocks session database fetch queries for API funnel tests."""
    monkeypatch.setattr(
        SessionRepository, "get_by_store_and_timerange", AsyncMock(return_value=[])
    )


@pytest.mark.asyncio
async def test_get_funnel_endpoint_empty_success(client: AsyncClient) -> None:
    """Verifies that queries for a valid store with zero sessions return 200 OK with zeroed steps."""
    response = await client.get("/api/v1/stores/STORE_BLR_002/funnel")
    assert response.status_code == 200

    data = response.json()
    assert data["store_id"] == "STORE_BLR_002"
    assert data["start_time"] is None
    assert data["end_time"] is None
    
    steps = data["steps"]
    assert len(steps) == 4
    assert steps[0]["step_name"] == "Store Entry"
    assert steps[0]["visitor_count"] == 0
    assert steps[0]["conversion_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_funnel_endpoint_time_filters(client: AsyncClient) -> None:
    """Verifies that the funnel API handles start_time and end_time parameters correctly."""
    response = await client.get(
        "/api/v1/stores/STORE_BLR_002/funnel",
        params={
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-31T23:59:59Z",
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_funnel_endpoint_invalid_store_format(
    client: AsyncClient,
) -> None:
    """Verifies that queries violating store_id format constraints raise 422 validation errors."""
    # Invalid store_id pattern (lacks STORE_ prefix)
    response = await client.get("/api/v1/stores/BLR_002/funnel")
    assert response.status_code == 422
