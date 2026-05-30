import pytest
from httpx import AsyncClient


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
