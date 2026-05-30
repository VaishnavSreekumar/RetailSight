from fastapi import APIRouter

from app.api.v1 import v1_router
from app.config import settings

api_router = APIRouter()

# Include version 1 API router under configured prefix
api_router.include_router(v1_router, prefix=settings.API_V1_STR)
