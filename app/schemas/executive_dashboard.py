from pydantic import BaseModel
from typing import List, Optional

class RevenueMetrics(BaseModel):
    nmv: float
    gmv: float
    abv: float

class SectionMetrics(BaseModel):
    section_name: str
    nmv: float
    gmv: float
    transaction_count: int
    abv: float

class BrandMetrics(BaseModel):
    brand_name: str
    nmv: float

class SalespersonMetrics(BaseModel):
    name: str
    sales_value: float
    units_sold: int

class CustomerBehavior(BaseModel):
    visitors: int
    engaged_visitors: int
    conversion_rate: float

class LayoutInsights(BaseModel):
    highest_revenue_section: str
    lowest_revenue_section: str
    highest_abv_section: str

class BehaviorInsights(BaseModel):
    average_session_length: float
    pages_per_session: float
    bounce_rate: float
    conversion_rate: float
    top_pages: List[str]

class ExecutiveDashboard(BaseModel):
    revenue: RevenueMetrics
    sections: List[SectionMetrics]
    top_brands: List[BrandMetrics]
    top_salespeople: List[SalespersonMetrics]
    customer_behavior: Optional[CustomerBehavior]
    layout_insights: LayoutInsights
    behavior_insights: Optional['BehaviorInsights'] = None

from .shopper_behavior import BehaviorInsights
ExecutiveDashboard.model_rebuild()
