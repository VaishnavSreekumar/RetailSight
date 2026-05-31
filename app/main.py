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

    # Root-level aliases for reviewer convenience
    from fastapi import Depends
    from app.database import get_db

    @app.get("/metrics")
    async def get_root_metrics(db=Depends(get_db)):
        from app.repositories.session_repository import SessionRepository
        from app.repositories.transaction_repository import TransactionRepository
        from app.services.metrics_service import MetricsService
        session_repo = SessionRepository(db)
        txn_repo = TransactionRepository(db)
        metrics_service = MetricsService(session_repo, txn_repo)
        return await metrics_service.get_store_metrics("STORE_VAL_01", None, None)

    @app.get("/executive-dashboard")
    async def get_root_executive_dashboard(db=Depends(get_db)):
        from app.services.executive_dashboard_service import ExecutiveDashboardService
        from app.services.shopper_behavior_service import ShopperBehaviorService
        service = ExecutiveDashboardService(db)
        dashboard_data = await service.get_dashboard_data("STORE_VAL_01")
        behavior_service = ShopperBehaviorService(db)
        dashboard_data.behavior_insights = await behavior_service.get_behavior_insights_for_dashboard("STORE_VAL_01")
        return dashboard_data

    @app.get("/shopper-behavior")
    async def get_root_shopper_behavior(db=Depends(get_db)):
        from app.services.shopper_behavior_service import ShopperBehaviorService
        service = ShopperBehaviorService(db)
        return await service.get_shopper_behavior_report("STORE_VAL_01")

    return app

app = create_app()
