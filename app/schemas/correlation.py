from pydantic import BaseModel, Field


class CorrelationTrackSchema(BaseModel):
    camera_id: str = Field(..., description="Normalized camera identifier (CAM1, CAM2, CAM4).")
    track_id: int = Field(..., description="Camera-local tracking ID integer.")


class GlobalVisitorCorrelationSchema(BaseModel):
    global_visitor_id: str = Field(..., description="Stitched global visitor ID.")
    tracks: list[CorrelationTrackSchema] = Field(..., description="List of local camera tracks stitched together.")
    confidence: str = Field(..., description="Correlation confidence (HIGH, MEDIUM, LOW).")


class CorrelationSummarySchema(BaseModel):
    total_global_visitors: int = Field(..., description="Total count of unique global visitors.")
    total_track_fragments: int = Field(..., description="Total count of stitched track fragments.")
    average_tracks_per_visitor: float = Field(..., description="Average track fragments per global visitor.")


class CorrelationDiagnosticsResponse(BaseModel):
    correlations: list[GlobalVisitorCorrelationSchema] = Field(..., description="List of all global visitor correlations.")
    summary: CorrelationSummarySchema = Field(..., description="Summary statistics of track stitching.")
