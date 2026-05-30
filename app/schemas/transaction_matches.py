from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class MatchedPairSchema(BaseModel):
    session_id: UUID = Field(..., description="Unique ID of the matched visitor session.")
    transaction_id: str = Field(..., description="Unique ID of the matched POS transaction.")
    match_score: float = Field(..., ge=0.0, le=100.0, description="Match score calculated by the decay and boost formula.")
    match_confidence: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$", description="Match confidence classification based on score.")


class UnmatchedSessionSchema(BaseModel):
    session_id: UUID = Field(..., description="Unique ID of the unmatched session.")
    visitor_id: str = Field(..., description="Visitor identifier associated with the session.")
    entered_at: datetime = Field(..., description="Date-time when the customer entered.")
    exited_at: datetime | None = Field(None, description="Date-time when the customer exited.")
    joined_billing_queue: bool = Field(..., description="Flag indicating if the customer joined checkout queue.")
    reason: str = Field(..., description="Explanation of why this session remained unmatched.")


class UnmatchedTransactionSchema(BaseModel):
    transaction_id: str = Field(..., description="Unique ID of the unmatched transaction.")
    timestamp: datetime = Field(..., description="Date-time when the checkout transaction occurred.")
    total_amount: float = Field(..., description="POS purchase total amount.")
    reason: str = Field(..., description="Explanation of why this transaction remained unmatched.")


class TransactionMatchesResponse(BaseModel):
    matched: list[MatchedPairSchema] = Field(..., description="List of matched session-transaction pairs.")
    unmatched_sessions: list[UnmatchedSessionSchema] = Field(..., description="List of unmatched visitor sessions with diagnostic reasons.")
    unmatched_transactions: list[UnmatchedTransactionSchema] = Field(..., description="List of unmatched transactions with diagnostic reasons.")
