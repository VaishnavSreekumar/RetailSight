from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.database import db_manager
from app.middleware.logging import LoggingMiddleware, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize logging configuration
    setup_logging()
    
    # Database engine initialization check
    await db_manager.check_connection()
    
    yield
    
    # Cleanup database connections on shutdown
    await db_manager.close()


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # Set up CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Set up custom structured logging middleware
    app.add_middleware(LoggingMiddleware)

    # Register API routers
    app.include_router(api_router)

    return app
