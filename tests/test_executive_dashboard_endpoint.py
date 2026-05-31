import pytest
from httpx import AsyncClient
from fastapi import status

@pytest.mark.asyncio
async def test_get_executive_dashboard(client: AsyncClient, test_db):
    """
    Tests the executive dashboard endpoint, ensuring it returns a valid
    and well-structured response based on the test dataset.
    """
    # The store_id is not actually used by the service yet, but is required by the path
    store_id = 123 
    
    response = await client.get(f"/api/v1/stores/{store_id}/executive-dashboard")

    assert response.status_code == status.HTTP_200_OK

    dashboard = response.json()

    # 1. Verify top-level structure
    expected_keys = [
        "revenue", "sections", "top_brands", 
        "top_salespeople", "customer_behavior", "layout_insights"
    ]
    assert all(key in dashboard for key in expected_keys)

    # 2. Verify Revenue Metrics
    revenue = dashboard["revenue"]
    assert "nmv" in revenue
    assert "gmv" in revenue
    assert "abv" in revenue
    assert revenue["nmv"] > 0
    assert revenue["gmv"] > 0
    assert revenue["abv"] > 0

    # 3. Verify Section Metrics
    sections = dashboard["sections"]
    assert isinstance(sections, list)
    assert len(sections) > 0
    first_section = sections[0]
    assert "section_name" in first_section
    assert "nmv" in first_section
    assert first_section["nmv"] > 0

    # 4. Verify Top Brands
    top_brands = dashboard["top_brands"]
    assert isinstance(top_brands, list)
    assert len(top_brands) > 0
    assert len(top_brands) <= 5
    first_brand = top_brands[0]
    assert "brand_name" in first_brand
    assert "nmv" in first_brand
    assert first_brand["nmv"] > 0

    # 5. Verify Layout Insights
    layout_insights = dashboard["layout_insights"]
    assert "highest_revenue_section" in layout_insights
    assert "lowest_revenue_section" in layout_insights
    assert "highest_abv_section" in layout_insights
    assert layout_insights["highest_revenue_section"] != ""

    # 6. Verify Salespeople and Customer Behavior
    assert len(dashboard["top_salespeople"]) > 0
    assert dashboard["customer_behavior"] is None

    import json
    print(json.dumps(dashboard, indent=4))
