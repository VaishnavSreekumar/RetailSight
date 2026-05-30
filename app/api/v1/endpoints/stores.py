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
from app.services.metrics_service import MetricsService
from app.services.funnel_service import FunnelService
from app.services.anomaly_service import AnomalyService

router = APIRouter()


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

