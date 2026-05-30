from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.config import settings
from app.database import db_manager

router = APIRouter()


class HealthResponse(BaseModel):
    """Schema representing system health check metrics."""

    status: str = Field(..., description="Overall status of the API instance.")
    database: str = Field(..., description="Database connectivity status.")
    environment: str = Field(..., description="Running deployment environment.")
    version: str = Field(..., description="App framework/platform version identifier.")


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve system health status",
)
async def check_health() -> HealthResponse:
    """Checks database and environment status to verify health."""
    db_connected = await db_manager.check_connection()
    db_status = "connected" if db_connected else "disconnected"
    overall_status = "healthy" if db_connected else "unhealthy"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        environment=settings.APP_ENV,
        version="1.0.0",
    )
