# PROMPT: Create service-layer test suite for calculating core store performance KPIs, ensuring staff exclusion.
# CHANGES MADE: Implemented unit tests verifying visitors, dwell time, and conversion metrics calculation while asserting staff exclusion.

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.visitor_session import VisitorSession
from app.services.metrics_service import MetricsService


@pytest.fixture
def mock_session_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_txn_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def metrics_service(mock_session_repo, mock_txn_repo) -> MetricsService:
    return MetricsService(mock_session_repo, mock_txn_repo)


@pytest.mark.asyncio
async def test_metrics_service_empty_store(
    metrics_service, mock_session_repo, mock_txn_repo
) -> None:
    """Verifies that queries for stores with zero sessions return zeroed metrics (no 404)."""
    mock_session_repo.get_by_store_and_timerange.return_value = []
    mock_txn_repo.get_by_store_and_timerange.return_value = []

    res = await metrics_service.get_store_metrics("STORE_BLR_002")

    assert res["store_id"] == "STORE_BLR_002"
    assert res["visitors"] == 0
    assert res["engaged_visitors"] == 0
    assert res["purchases"] == 0
    assert res["conversion_rate"] == 0.0
    assert res["avg_session_dwell_ms"] == 0.0
    assert res["avg_journey_length"] == 0.0
    assert res["avg_zones_visited"] == 0.0
    assert res["opportunity_zones"] == []


@pytest.mark.asyncio
async def test_metrics_service_normal_calculation(
    metrics_service, mock_session_repo, mock_txn_repo
) -> None:
    """Verifies correct calculation of dwell times, conversions, and zones."""
    sessions = [
        # Session 1: Engaged, converted, dwell 300s, 2 zones visited
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_c8a2f1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc),
            journey_path=["zone_electronics", "zone_apparel"],
            zone_dwell_times={"zone_electronics": 100000, "zone_apparel": 200000},
            has_joined_billing_queue=True,
            has_converted=True,
        ),
        # Session 2: Engaged, not converted, dwell 100s, 1 zone visited
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_a9b1c2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 11, 40, tzinfo=timezone.utc),
            journey_path=["zone_electronics"],
            zone_dwell_times={"zone_electronics": 100000},
            has_joined_billing_queue=False,
            has_converted=False,
        ),
    ]
    mock_session_repo.get_by_store_and_timerange.return_value = sessions

    res = await metrics_service.get_store_metrics("STORE_BLR_002")

    assert res["store_id"] == "STORE_BLR_002"
    assert res["visitors"] == 2
    assert res["engaged_visitors"] == 2
    assert res["purchases"] == 1
    assert res["conversion_rate"] == 50.0
    # Dwell averages: (300000 + 100000) / 2 = 200000.0 ms
    assert res["avg_session_dwell_ms"] == 200000.0
    # Journey lengths: (2 + 1) / 2 = 1.5
    assert res["avg_journey_length"] == 1.5
    # Unique zones visited count matches journey paths: (2 + 1) / 2 = 1.5
    assert res["avg_zones_visited"] == 1.5


@pytest.mark.asyncio
async def test_metrics_service_opportunity_detection(
    metrics_service, mock_session_repo, mock_txn_repo
) -> None:
    """Verifies that zones violating performance parameters are flagged as opportunity zones."""
    sessions = [
        # Session 1: High dwell on apparel, no billing join, no purchase
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_c8a2f1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 8, 20, tzinfo=timezone.utc),
            journey_path=["zone_apparel"],
            zone_dwell_times={"zone_apparel": 500000},
            has_joined_billing_queue=False,
            has_converted=False,
        ),
        # Session 2: Low dwell on electronics, joins billing, purchase
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_a9b1c2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 10, 50, tzinfo=timezone.utc),
            journey_path=["zone_electronics"],
            zone_dwell_times={"zone_electronics": 50000},
            has_joined_billing_queue=True,
            has_converted=True,
        ),
    ]
    mock_session_repo.get_by_store_and_timerange.return_value = sessions

    res = await metrics_service.get_store_metrics("STORE_BLR_002")

    assert len(res["opportunity_zones"]) == 1
    flagged = res["opportunity_zones"][0]
    assert flagged["zone"] == "zone_apparel"
    assert flagged["severity"] == "HIGH"
    assert flagged["reason"] == "High dwell but low billing progression"


@pytest.mark.asyncio
async def test_metrics_service_retail_zone_filtering(
    metrics_service, mock_session_repo, mock_txn_repo
) -> None:
    """Verifies that non-retail zones like ENTRY, EXIT, BILLING, REENTRY are excluded from unique retail zones visited count."""
    sessions = [
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_c8a2f1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc),
            journey_path=["zone_entry", "zone_electronics", "zone_billing", "zone_apparel", "zone_exit"],
            zone_dwell_times={"zone_electronics": 100000, "zone_apparel": 200000},
            has_joined_billing_queue=True,
            has_converted=True,
        ),
    ]
    mock_session_repo.get_by_store_and_timerange.return_value = sessions

    res = await metrics_service.get_store_metrics("STORE_BLR_002")

    # avg_journey_length counts everything in journey_path: 5
    assert res["avg_journey_length"] == 5.0
    # avg_zones_visited counts only retail zones ("zone_electronics", "zone_apparel"): 2
    assert res["avg_zones_visited"] == 2.0


@pytest.mark.asyncio
async def test_metrics_service_excludes_staff(
    metrics_service, mock_session_repo, mock_txn_repo
) -> None:
    """Verifies that sessions flagged as staff (is_staff=True) are completely excluded from calculated metrics."""
    sessions = [
        # Customer session (engaged, converted, dwell 300s)
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_cust01",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc),
            journey_path=["zone_electronics"],
            zone_dwell_times={"zone_electronics": 300000},
            has_joined_billing_queue=True,
            has_converted=True,
            is_staff=False,
        ),
        # Staff session (should be ignored)
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_staff01",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
            journey_path=["zone_electronics"],
            zone_dwell_times={"zone_electronics": 600000},
            has_joined_billing_queue=True,
            has_converted=True,
            is_staff=True,
        ),
    ]
    mock_session_repo.get_by_store_and_timerange.return_value = sessions

    res = await metrics_service.get_store_metrics("STORE_BLR_002")

    # Metrics should only count the 1 customer session, completely ignoring the staff session
    assert res["visitors"] == 1
    assert res["engaged_visitors"] == 1
    assert res["purchases"] == 1
    assert res["conversion_rate"] == 100.0
    assert res["avg_session_dwell_ms"] == 300000.0
