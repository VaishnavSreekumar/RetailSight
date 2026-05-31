from datetime import datetime
from pydantic import BaseModel, Field


class OpportunityZoneResponse(BaseModel):
    """Schema representing details of a zone marked for opportunity loss analysis."""

    zone: str = Field(..., description="The unique zone identifier.")
    avg_dwell_ms: float = Field(
        ..., description="Average dwell time spent in the zone in milliseconds."
    )
    conversion_rate: float = Field(
        ..., description="Conversion rate of visitors who entered this zone."
    )
    billing_progression_rate: float = Field(
        ...,
        description="Percentage of this zone's visitors who joined the billing queue.",
    )
    severity: str = Field(
        ..., description="Calculated urgency tier (e.g. HIGH, MEDIUM, LOW)."
    )
    reason: str = Field(
        ..., description="Specific performance criteria driving the audit alert."
    )


class StoreMetrics(BaseModel):
    """Schema representing consolidated retail metrics summary for a store."""

    store_id: str = Field(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="String identifier matching STORE_BLR_002 format.",
    )
    visitors: int = Field(
        ..., description="Total count of unique visitor session entries."
    )
    engaged_visitors: int = Field(
        ..., description="Count of visitors who navigated to at least one store zone."
    )
    billing_queue_visitors: int = Field(
        ..., description="Count of visitors who queued for checkouts."
    )
    purchases: int = Field(
        ..., description="Count of visitors completing sales transactions."
    )
    conversion_rate: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall store purchase conversion rate as a percentage (0.0–100.0). "
                    "Formula: (purchases / total_entries) * 100.",
    )
    avg_session_dwell_ms: float = Field(
        ..., description="Average shopping session dwell duration in milliseconds."
    )
    avg_journey_length: float = Field(
        ..., description="Average count of unique zones visited per session."
    )
    avg_zones_visited: float = Field(
        ..., description="Average count of unique retail zones visited per session."
    )
    opportunity_zones: list[OpportunityZoneResponse] = Field(
        ..., description="Structured audit reports for opportunity loss zones."
    )
    generated_at: datetime = Field(
        ..., description="Timestamp representing when metrics were aggregated."
    )


class ZoneMetrics(BaseModel):
    """Schema representing traffic metric KPIs for a specific store zone."""

    zone_id: str = Field(..., description="The coordinate zone identifier.")
    visitor_count: int = Field(..., description="Count of unique visitors in the zone.")
    average_dwell_ms: float = Field(
        ..., description="Average dwell duration inside this zone in milliseconds."
    )
