from pydantic import BaseModel
from typing import List, Optional

class SectionBehaviorMetrics(BaseModel):
    section_name: str
    visitor_count: int
    avg_dwell_seconds: float
    purchase_count: int
    conversion_rate: float

class OpportunityZone(BaseModel):
    section_name: str
    recommendation: str

class CheckoutIntelligence(BaseModel):
    queue_entries: int
    completed_purchases: int
    abandonment_rate: float
    estimated_lost_revenue: float

class ShopperBehaviorReport(BaseModel):
    sections: List[SectionBehaviorMetrics]
    opportunity_zones: List[OpportunityZone]
    checkout_intelligence: CheckoutIntelligence

class BehaviorInsights(BaseModel):
    best_converting_section: Optional[str] = None
    worst_converting_section: Optional[str] = None
    highest_dwell_section: Optional[str] = None
