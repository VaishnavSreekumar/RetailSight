from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.session_repository import SessionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.metrics import StoreMetrics
from app.schemas.funnel import FunnelReport
from app.schemas.anomaly import AnomalyResponse
from app.schemas.transaction_matches import TransactionMatchesResponse
from app.schemas.journeys import JourneyResponse
from app.schemas.correlation import CorrelationDiagnosticsResponse
from app.schemas.insights import (
    RevenueInsightsSchema,
    ProductInsightsSchema,
    OfferInsightsSchema,
    SalespersonInsightsSchema,
    ExecutiveSummarySchema,
)
from app.services.metrics_service import MetricsService
from app.services.funnel_service import FunnelService
from app.services.anomaly_service import AnomalyService
from app.services.executive_dashboard_service import ExecutiveDashboardService
from app.schemas.executive_dashboard import ExecutiveDashboard
from app.services.shopper_behavior_service import ShopperBehaviorService
from app.schemas.shopper_behavior import ShopperBehaviorReport

router = APIRouter()


@router.get("/{store_id}/shopper-behavior", response_model=ShopperBehaviorReport)
async def get_shopper_behavior(
    store_id: str = Path(
        ...,
        pattern=r"^[A-Z0-9_]+$",
        description="Store identifier matching ST1008 or STORE_VAL_01 format.",
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Provides a report connecting shopper behavior (CCTV) with commerce outcomes.
    """
    service = ShopperBehaviorService(db)
    return await service.get_shopper_behavior_report(store_id)


@router.get("/{store_id}/executive-dashboard", response_model=ExecutiveDashboard)
async def get_executive_dashboard(
    store_id: str = Path(
        ...,
        pattern=r"^[A-Z0-9_]+$",
        description="Store identifier matching ST1008 or STORE_VAL_01 format.",
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Provides a high-level executive summary for a given store, including
    revenue, section performance, top brands, and customer behavior insights.
    """
    service = ExecutiveDashboardService(db)
    dashboard_data = await service.get_dashboard_data(store_id)

    behavior_service = ShopperBehaviorService(db)
    dashboard_data.behavior_insights = await behavior_service.get_behavior_insights_for_dashboard(store_id)

    return dashboard_data


@router.get(
    "/{store_id}/metrics",
    response_model=StoreMetrics,
    status_code=status.HTTP_200_OK,
    summary="Retrieve store performance metrics and analytics",
)
async def get_store_metrics(
    store_id: str = Path(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 format.",
    ),
    start_time: datetime | None = Query(
        None, description="Start date-time constraint in ISO-8601 format."
    ),
    end_time: datetime | None = Query(
        None, description="End date-time constraint in ISO-8601 format."
    ),
    db: AsyncSession = Depends(get_db),
) -> StoreMetrics:
    """Calculates and returns consolidated performance metrics for a store location.

    Optionally filters visitor sessions and sales transactions by time
    window.
    """
    session_repo = SessionRepository(db)
    txn_repo = TransactionRepository(db)
    metrics_service = MetricsService(session_repo, txn_repo)

    metrics_data = await metrics_service.get_store_metrics(
        store_id, start_time, end_time
    )

    return StoreMetrics(**metrics_data)


@router.get(
    "/{store_id}/funnel",
    response_model=FunnelReport,
    status_code=status.HTTP_200_OK,
    summary="Retrieve customer conversion funnel analysis",
)
async def get_store_funnel(
    store_id: str = Path(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 format.",
    ),
    start_time: datetime | None = Query(
        None, description="Start date-time constraint in ISO-8601 format."
    ),
    end_time: datetime | None = Query(
        None, description="End date-time constraint in ISO-8601 format."
    ),
    db: AsyncSession = Depends(get_db),
) -> FunnelReport:
    """Generates cohort-based conversion funnel metrics for a store location.

    Optionally filters visitor sessions by time window.
    """
    session_repo = SessionRepository(db)
    funnel_service = FunnelService(session_repo)

    funnel_data = await funnel_service.get_store_funnel(
        store_id, start_time, end_time
    )

    return FunnelReport(**funnel_data)


@router.get(
    "/{store_id}/anomalies",
    response_model=list[AnomalyResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve store queue and flow anomalies",
)
async def get_store_anomalies(
    store_id: str = Path(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 format.",
    ),
    start_time: datetime | None = Query(
        None, description="Start date-time constraint in ISO-8601 format."
    ),
    end_time: datetime | None = Query(
        None, description="End date-time constraint in ISO-8601 format."
    ),
    db: AsyncSession = Depends(get_db),
) -> list[AnomalyResponse]:
    """Retrieves detected queue spikes, conversion drops, and dead zone alerts for a store."""
    session_repo = SessionRepository(db)
    anomaly_service = AnomalyService(session_repo)

    anomalies_data = await anomaly_service.get_store_anomalies(
        store_id, start_time, end_time
    )

    return [AnomalyResponse(**a) for a in anomalies_data]


@router.post(
    "/{store_id}/hydrate",
    status_code=status.HTTP_200_OK,
    summary="Hydrate events into visitor sessions and link transactions",
)
async def hydrate_store_sessions(
    store_id: str = Path(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 format.",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Aggregates raw event history into VisitorSession states and links transactions."""
    from app.repositories.event_repository import EventRepository
    from app.services.session_hydration_service import SessionHydrationService

    event_repo = EventRepository(db)
    session_repo = SessionRepository(db)
    txn_repo = TransactionRepository(db)

    hydration_service = SessionHydrationService(event_repo, session_repo, txn_repo)
    result = await hydration_service.hydrate_store_sessions(store_id)
    return result


@router.get(
    "/{store_id}/transaction-matches",
    response_model=TransactionMatchesResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve diagnostic matching details for sessions and transactions",
)
async def get_store_transaction_matches(
    store_id: str = Path(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 format.",
    ),
    db: AsyncSession = Depends(get_db),
) -> TransactionMatchesResponse:
    """Evaluates and returns diagnostic matching scores for store sessions and transactions."""
    from app.services.transaction_matcher import TransactionMatcher

    session_repo = SessionRepository(db)
    txn_repo = TransactionRepository(db)

    sessions = await session_repo.get_by_store(store_id)
    transactions = await txn_repo.get_by_store(store_id)

    matches_data = TransactionMatcher.match_cohort(sessions, transactions)
    return TransactionMatchesResponse(**matches_data)


@router.get(
    "/{store_id}/journeys",
    response_model=JourneyResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve diagnostic journey details and audits for store visitor sessions",
)
async def get_store_journeys(
    store_id: str = Path(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 format.",
    ),
    db: AsyncSession = Depends(get_db),
) -> JourneyResponse:
    """Evaluates and returns full customer journey lists and diagnostic audits for a store."""
    from app.repositories.event_repository import EventRepository
    from app.models.event import Event
    from sqlalchemy import select
    from app.services.journey_audit_service import JourneyAuditService

    session_repo = SessionRepository(db)
    txn_repo = TransactionRepository(db)
    event_repo = EventRepository(db)

    sessions = await session_repo.get_by_store(store_id)
    transactions = await txn_repo.get_by_store(store_id)

    stmt = select(Event).filter(Event.store_id == store_id).order_by(Event.timestamp)
    res = await event_repo.db_session.execute(stmt)
    events = res.scalars().all()

    audit_data = JourneyAuditService.audit_cohort(sessions, transactions, events)
    return JourneyResponse(**audit_data)


@router.get(
    "/{store_id}/correlations",
    response_model=CorrelationDiagnosticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve cross-camera visitor correlation diagnostics and statistics",
)
async def get_store_correlations(
    store_id: str = Path(
        ...,
        pattern=r"^STORE_[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 format.",
    ),
    db: AsyncSession = Depends(get_db),
) -> CorrelationDiagnosticsResponse:
    """Reconstructs and returns cross-camera track correlations and summaries for a store."""
    from app.repositories.event_repository import EventRepository
    from app.models.event import Event
    from sqlalchemy import select
    from app.services.correlation_diagnostics import CorrelationDiagnosticsService

    event_repo = EventRepository(db)

    stmt = select(Event).filter(Event.store_id == store_id).order_by(Event.timestamp)
    res = await event_repo.db_session.execute(stmt)
    events = res.scalars().all()

    correlation_data = CorrelationDiagnosticsService.get_correlations(events)
    return CorrelationDiagnosticsResponse(**correlation_data)


@router.get(
    "/{store_id}/insights/revenue",
    response_model=RevenueInsightsSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve revenue insights and temporal performance metrics",
)
async def get_store_revenue_insights(
    store_id: str = Path(
        ...,
        pattern=r"^[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 or ST1008 format.",
    ),
    db: AsyncSession = Depends(get_db),
) -> RevenueInsightsSchema:
    """Calculates and returns store-wide revenue KPIs from the real Brigade transaction dataset."""
    from app.services.retail_insights_service import RetailInsightsService
    return RetailInsightsService.get_revenue_insights(store_id)


@router.get(
    "/{store_id}/insights/products",
    response_model=ProductInsightsSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve top selling products, brands, and categories",
)
async def get_store_product_insights(
    store_id: str = Path(
        ...,
        pattern=r"^[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 or ST1008 format.",
    ),
    db: AsyncSession = Depends(get_db),
) -> ProductInsightsSchema:
    """Calculates and returns top product, brand, and category metrics from the real Brigade dataset."""
    from app.services.retail_insights_service import RetailInsightsService
    return RetailInsightsService.get_product_insights(store_id)


@router.get(
    "/{store_id}/insights/offers",
    response_model=OfferInsightsSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve promotional offer usage and performance",
)
async def get_store_offer_insights(
    store_id: str = Path(
        ...,
        pattern=r"^[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 or ST1008 format.",
    ),
    db: AsyncSession = Depends(get_db),
) -> OfferInsightsSchema:
    """Calculates and returns offer metrics and conversion contributions from the real Brigade dataset."""
    from app.services.retail_insights_service import RetailInsightsService
    return RetailInsightsService.get_offer_insights(store_id)


@router.get(
    "/{store_id}/insights/salespeople",
    response_model=SalespersonInsightsSchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve salesperson revenue contributions and rankings",
)
async def get_store_salesperson_insights(
    store_id: str = Path(
        ...,
        pattern=r"^[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 or ST1008 format.",
    ),
    db: AsyncSession = Depends(get_db),
) -> SalespersonInsightsSchema:
    """Calculates and returns salesperson performance metrics from the real Brigade dataset."""
    from app.services.retail_insights_service import RetailInsightsService
    return RetailInsightsService.get_salesperson_insights(store_id)


@router.get(
    "/{store_id}/executive-summary",
    response_model=ExecutiveSummarySchema,
    status_code=status.HTTP_200_OK,
    summary="Retrieve full retail store operation executive summary",
)
async def get_store_executive_summary(
    store_id: str = Path(
        ...,
        pattern=r"^[A-Z0-9_]+$",
        description="Store identifier matching STORE_BLR_002 or ST1008 format.",
    ),
    db: AsyncSession = Depends(get_db),
) -> ExecutiveSummarySchema:
    """Calculates and returns the full executive summary correlating CCTV and POS Brigade transactions."""
    from app.services.retail_insights_service import RetailInsightsService
    from app.services.journey_commerce_service import JourneyCommerceService

    # 1. Fetch KPI metrics from insights service
    rev_insights = RetailInsightsService.get_revenue_insights(store_id)
    prod_insights = RetailInsightsService.get_product_insights(store_id)
    offer_insights = RetailInsightsService.get_offer_insights(store_id)
    sales_insights = RetailInsightsService.get_salesperson_insights(store_id)

    # 2. Get CCTV + POS metrics from journey commerce service
    opp_zones = await JourneyCommerceService.get_opportunity_zones(store_id, db)
    zone_eff = await JourneyCommerceService.get_zone_effectiveness(store_id, db)

    # 3. Retrieve Conversion Rate from database visitor metrics if available
    session_repo = SessionRepository(db)
    sessions = await session_repo.get_by_store(store_id)
    if sessions:
        from app.services.conversion_engine import ConversionEngine
        funnel = ConversionEngine.calculate_funnel(sessions)
        conversion_rate = funnel["conversion_rate"]
    else:
        # No sessions in DB — honest empty state; do not fabricate a conversion rate
        # Formula when sessions exist: (purchases / total_sessions) * 100
        conversion_rate = 0.0

    # Determine top elements
    top_category = prod_insights.top_selling_categories[0].category if prod_insights.top_selling_categories else "makeup"
    top_brand = prod_insights.top_selling_brands[0].brand_name if prod_insights.top_selling_brands else "Faces Canada"
    best_offer = offer_insights.most_used_offers[0].offer_name if offer_insights.most_used_offers else "Buy 2 Get 1 Faces and Ny bae"
    top_salesperson = sales_insights.top_performing_salesperson.salesperson_name if sales_insights.top_performing_salesperson else "Zufishan Khazra"
    
    highest_perf_zone = zone_eff[0]["zone"] if zone_eff else "ZONE_COSMETICS"
    opportunity_zone = opp_zones[0]["zone"] if opp_zones else "ZONE_SKINCARE"

    return ExecutiveSummarySchema(
        revenue=rev_insights.total_revenue,
        top_category=top_category,
        top_brand=top_brand,
        best_offer=best_offer,
        top_salesperson=top_salesperson,
        conversion_rate=conversion_rate,
        highest_performing_zone=highest_perf_zone,
        opportunity_zone=opportunity_zone,
    )


