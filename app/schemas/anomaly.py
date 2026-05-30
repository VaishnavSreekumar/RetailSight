from datetime import datetime
from pydantic import BaseModel, Field


class AnomalyResponse(BaseModel):
    """Schema representing a detected store queue or zone flow anomaly."""

    type: str = Field(..., description="Anomaly classification type (e.g. QUEUE_SPIKE).")
    severity: str = Field(..., description="Urgency rating (e.g. HIGH, MEDIUM, LOW).")
    title: str = Field(..., description="Short descriptive headline.")
    description: str = Field(..., description="Detailed description of the flagged anomaly.")
    affected_zone: str | None = Field(None, description="Retail zone identifier if applicable.")
    suggested_action: str = Field(..., description="Recommended mitigation step.")
    metric_value: float | None = Field(None, description="Current metric value driving the alert.")
    baseline_value: float | None = Field(None, description="Baseline metric value compared against.")
    generated_at: datetime = Field(..., description="Timestamp when anomaly check ran.")
