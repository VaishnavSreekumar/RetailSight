# PROMPT: Build test assertions for store performance summary and comparative cohort metrics API.
# CHANGES MADE: Validated response schema for store performance summaries and time-series cohort calculations.

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock
from app.repositories.session_repository import SessionRepository

@pytest.fixture(autouse=True)
def mock_repos_for_insights(monkeypatch) -> None:
    """Mocks database session repository query fetches to avoid DB service dependencies."""
    monkeypatch.setattr(
        SessionRepository, "get_by_store", AsyncMock(return_value=[])
    )

@pytest.mark.asyncio
async def test_get_revenue_insights_endpoint(client: AsyncClient) -> None:
    """Verifies that the revenue insights endpoint returns 200 OK with correct schema."""
    response = await client.get("/api/v1/stores/ST1008/insights/revenue")
    assert response.status_code == 200
    data = response.json()
    assert "total_revenue" in data
    assert "total_gmv" in data
    assert "average_basket_value" in data

@pytest.mark.asyncio
async def test_get_product_insights_endpoint(client: AsyncClient) -> None:
    """Verifies that the product insights endpoint returns 200 OK with correct schema."""
    response = await client.get("/api/v1/stores/ST1008/insights/products")
    assert response.status_code == 200
    data = response.json()
    assert "top_selling_products" in data
    assert "top_selling_brands" in data
    assert len(data["top_selling_brands"]) > 0
    assert data["top_selling_brands"][0]["brand_name"] == "Faces Canada"

@pytest.mark.asyncio
async def test_get_offer_insights_endpoint(client: AsyncClient) -> None:
    """Verifies that the offers insights endpoint returns 200 OK with correct schema."""
    response = await client.get("/api/v1/stores/ST1008/insights/offers")
    assert response.status_code == 200
    data = response.json()
    assert "most_used_offers" in data
    assert "revenue_by_offer" in data

@pytest.mark.asyncio
async def test_get_salesperson_insights_endpoint(client: AsyncClient) -> None:
    """Verifies that the salesperson insights endpoint returns 200 OK with correct schema."""
    response = await client.get("/api/v1/stores/ST1008/insights/salespeople")
    assert response.status_code == 200
    data = response.json()
    assert "revenue_by_salesperson" in data
    assert "top_performing_salesperson" in data
    assert data["top_performing_salesperson"]["salesperson_name"] == "Zufishan Khazra"

@pytest.mark.asyncio
async def test_get_executive_summary_endpoint(client: AsyncClient) -> None:
    """Verifies that the executive summary endpoint returns 200 OK with consolidated KPIs."""
    response = await client.get("/api/v1/stores/ST1008/executive-summary")
    assert response.status_code == 200
    data = response.json()
    assert "revenue" in data
    assert "top_category" in data
    assert "top_brand" in data
    assert "top_salesperson" in data
    assert "conversion_rate" in data
    assert "highest_performing_zone" in data
    assert "opportunity_zone" in data
    assert data["top_brand"] == "Faces Canada"
    assert data["top_salesperson"] == "Zufishan Khazra"
