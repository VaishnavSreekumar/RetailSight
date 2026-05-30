from fastapi import APIRouter

from app.api.v1.endpoints import (
    events,
    health,
    heatmap,
    stores,
)

v1_router = APIRouter()

# Mount endpoints under V1 namespace
v1_router.include_router(health.router, tags=["Health"])
v1_router.include_router(events.router, prefix="/events", tags=["Events"])
v1_router.include_router(stores.router, prefix="/stores", tags=["Stores"])
v1_router.include_router(heatmap.router, prefix="/heatmap", tags=["Heatmap"])
