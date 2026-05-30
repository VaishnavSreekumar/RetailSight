from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FunnelStep(BaseModel):
    """Schema representing a single milestone step in a conversion funnel."""

    step_name: str = Field(
        ..., description="Name representing the stage (e.g. entry, checkout)."
    )
    visitor_count: int = Field(
        ..., description="Total count of visitors reaching this funnel step."
    )
    conversion_rate: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of preceding step visitors reaching this step.",
    )


class FunnelReport(BaseModel):
    """Schema representing conversion funnel analytics for a store."""

    store_id: str = Field(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="String identifier matching STORE_BLR_002 format.",
    )
    start_time: datetime | None = Field(None, description="Funnel cohort start time.")
    end_time: datetime | None = Field(None, description="Funnel cohort end time.")
    steps: list[FunnelStep] = Field(
        ..., description="Ordered list of milestone stages in this funnel."
    )
