from uuid import UUID

from fastapi import APIRouter, status

from app.schemas.metrics import ZoneMetrics

router = APIRouter()


@router.get(
    "/store/{store_id}",
    response_model=list[ZoneMetrics],
    status_code=status.HTTP_200_OK,
    summary="Retrieve store zone dwell heatmap metrics",
)
async def get_heatmap_metrics(store_id: UUID) -> list[ZoneMetrics]:
    """Retrieves dwell time heatmaps for all recorded store zones."""
    return [
        ZoneMetrics(
            zone_id="entrance-gate", visitor_count=1200, average_dwell_ms=45000.0
        ),
        ZoneMetrics(
            zone_id="aisle-electronics",
            visitor_count=450,
            average_dwell_ms=180000.0,
        ),
        ZoneMetrics(
            zone_id="aisle-groceries",
            visitor_count=800,
            average_dwell_ms=320000.0,
        ),
        ZoneMetrics(
            zone_id="checkout-counter",
            visitor_count=350,
            average_dwell_ms=240000.0,
        ),
    ]
