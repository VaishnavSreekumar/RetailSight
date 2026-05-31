from pydantic import BaseModel, Field
from typing import List, Dict

class RevenueHourlySchema(BaseModel):
    hour: int
    revenue: float
    order_count: int

class RevenueDailySchema(BaseModel):
    date: str
    revenue: float
    order_count: int

class RevenueInsightsSchema(BaseModel):
    total_revenue: float = Field(..., description="Total Net Merchandise Value (NMV)")
    total_gmv: float = Field(..., description="Total Gross Merchandise Value (GMV)")
    total_discount: float = Field(..., description="Total Applied Discounts")
    average_basket_value: float = Field(..., description="Average NMV per order")
    average_items_per_basket: float = Field(..., description="Average items per order")
    revenue_by_day: List[RevenueDailySchema]
    revenue_by_hour: List[RevenueHourlySchema]


class ProductKPIItem(BaseModel):
    sku: str
    product_name: str
    quantity: int
    revenue: float

class BrandKPIItem(BaseModel):
    brand_name: str
    quantity: int
    revenue: float

class CategoryKPIItem(BaseModel):
    category: str
    quantity: int
    revenue: float

class SubcategoryKPIItem(BaseModel):
    subcategory: str
    quantity: int
    revenue: float

class ProductInsightsSchema(BaseModel):
    top_selling_products: List[ProductKPIItem]
    top_selling_brands: List[BrandKPIItem]
    top_selling_categories: List[CategoryKPIItem]
    top_selling_subcategories: List[SubcategoryKPIItem]


class OfferKPIItem(BaseModel):
    offer_name: str
    count: int
    revenue: float
    order_count: int
    conversion_contribution: float = Field(..., description="Percentage of total revenue contributed by this offer")

class OfferInsightsSchema(BaseModel):
    most_used_offers: List[OfferKPIItem]
    revenue_by_offer: Dict[str, float]
    orders_by_offer: Dict[str, int]


class SalespersonKPIItem(BaseModel):
    salesperson_name: str
    employee_code: str
    revenue: float
    order_count: int

class SalespersonInsightsSchema(BaseModel):
    revenue_by_salesperson: List[SalespersonKPIItem]
    top_performing_salesperson: SalespersonKPIItem | None


class ExecutiveSummarySchema(BaseModel):
    revenue: float = Field(..., description="Total store revenue (NMV)")
    top_category: str = Field(..., description="Top selling department by revenue")
    top_brand: str = Field(..., description="Top selling brand by revenue")
    best_offer: str = Field(..., description="Most successful or used offer campaign")
    top_salesperson: str = Field(..., description="Salesperson with highest NMV generation")
    conversion_rate: float = Field(..., description="Overall visitor conversion rate percentage")
    highest_performing_zone: str = Field(..., description="Zone with highest conversion or engagement")
    opportunity_zone: str = Field(..., description="Zone with high dwell but low conversion")
