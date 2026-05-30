from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class JourneyAssociatedTransactionSchema(BaseModel):
    transaction_id: str = Field(..., description="Unique ID of the POS transaction.")
    timestamp: datetime = Field(..., description="Date-time when the transaction occurred.")
    total_amount: float = Field(..., description="Purchase total amount.")


class JourneySchema(BaseModel):
    session_id: UUID = Field(..., description="Unique ID of the visitor session.")
    visitor_id: str = Field(..., description="Visitor identifier associated with the session.")
    journey_path: list[str] = Field(..., description="Sequential list of retail zone IDs visited.")
    entered_at: datetime = Field(..., description="Timestamp of store entry.")
    exited_at: datetime | None = Field(None, description="Timestamp of store exit.")
    zones_visited: list[str] = Field(..., description="List of unique retail zone names visited.")
    joined_billing_queue: bool = Field(..., description="Flag indicating if the visitor joined checkout queue.")
    associated_transaction: JourneyAssociatedTransactionSchema | None = Field(None, description="Details of the matched transaction, if any.")
    event_count: int = Field(..., description="Total count of raw events mapping to this session.")
    session_duration_ms: float = Field(..., description="Total session duration in milliseconds.")


class JourneyAuditSchema(BaseModel):
    longest_journeys: list[JourneySchema] = Field(..., description="Top 10 longest visitor sessions by dwell time.")
    billing_queue_no_purchase: list[JourneySchema] = Field(..., description="Visitor sessions that joined queue but did not purchase.")
    purchase_no_retail_zones: list[JourneySchema] = Field(..., description="Visitor sessions with purchase but no retail zones visited.")
    entry_exit_only: list[JourneySchema] = Field(..., description="Visitor sessions with entry/exit events only.")
    single_zone_sessions: list[JourneySchema] = Field(..., description="Visitor sessions visiting exactly one retail zone.")


class JourneyResponse(BaseModel):
    journeys: list[JourneySchema] = Field(..., description="Full list of reconstructed customer journeys.")
    audit: JourneyAuditSchema = Field(..., description="Detailed audit categorization results.")
