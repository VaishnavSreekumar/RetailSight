import pytest
from app.services.retail_insights_service import RetailInsightsService
from app.schemas.insights import (
    RevenueInsightsSchema,
    ProductInsightsSchema,
    OfferInsightsSchema,
    SalespersonInsightsSchema,
)

def test_retail_insights_service_revenue():
    """Verifies that the retail insights service calculates all revenue KPIs correctly."""
    res = RetailInsightsService.get_revenue_insights("ST1008")
    
    assert isinstance(res, RevenueInsightsSchema)
    assert res.total_revenue == 34831.74
    assert res.total_gmv == 44920.0
    assert res.total_discount == 10088.26
    assert res.average_basket_value == 1451.32
    assert res.average_items_per_basket == 4.88
    assert len(res.revenue_by_day) > 0
    assert len(res.revenue_by_hour) > 0

def test_retail_insights_service_products():
    """Verifies that the product KPIs are processed and sorted correctly."""
    res = RetailInsightsService.get_product_insights("ST1008")
    
    assert isinstance(res, ProductInsightsSchema)
    assert len(res.top_selling_products) > 0
    assert len(res.top_selling_brands) > 0
    assert len(res.top_selling_categories) > 0
    assert len(res.top_selling_subcategories) > 0

    # Faces Canada must be top brand
    assert res.top_selling_brands[0].brand_name == "Faces Canada"
    assert res.top_selling_categories[0].category == "makeup"

def test_retail_insights_service_offers():
    """Verifies that applied promotional offers are tracked accurately."""
    res = RetailInsightsService.get_offer_insights("ST1008")
    
    assert isinstance(res, OfferInsightsSchema)
    assert len(res.most_used_offers) > 0
    assert "Buy 2 Get 1 Faces and Ny bae" in res.revenue_by_offer
    assert res.orders_by_offer["Buy 2 Get 1 Faces and Ny bae"] > 0

def test_retail_insights_service_salespeople():
    """Verifies that salesperson revenue contribution metrics are correct."""
    res = RetailInsightsService.get_salesperson_insights("ST1008")
    
    assert isinstance(res, SalespersonInsightsSchema)
    assert len(res.revenue_by_salesperson) > 0
    assert res.top_performing_salesperson is not None
    assert res.top_performing_salesperson.salesperson_name == "Zufishan Khazra"
