# PROMPT: Create service-layer test suite for the conversion funnel calculation metrics, ensuring staff exclusion.
# CHANGES MADE: Implemented unit tests verifying visitor progression through funnel stages, and asserting complete exclusion of staff sessions.

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.visitor_session import VisitorSession
from app.services.funnel_service import FunnelService


@pytest.fixture
def mock_session_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def funnel_service(mock_session_repo) -> FunnelService:
    return FunnelService(mock_session_repo)


@pytest.mark.asyncio
async def test_funnel_service_empty_cohort(funnel_service, mock_session_repo) -> None:
    """Verifies that an empty visitor cohort returns zero counts and rates for all steps."""
    mock_session_repo.get_by_store_and_timerange.return_value = []
    
    res = await funnel_service.get_store_funnel("STORE_BLR_002")

    assert res["store_id"] == "STORE_BLR_002"
    assert res["start_time"] is None
    assert res["end_time"] is None
    
    steps = res["steps"]
    assert len(steps) == 4
    for step in steps:
        assert step["visitor_count"] == 0
        assert step["conversion_rate"] == 0.0


@pytest.mark.asyncio
async def test_funnel_service_calculations(funnel_service, mock_session_repo) -> None:
    """Verifies correct visitor counts and relative conversion rates per step."""
    sessions = [
        # Session 1: Store entry (entries=4), Browsing Zones (engaged=3), Checkout (billing=2), Converted (purchased=1)
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_c8a2f1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc),
            journey_path=["zone_apparel"],
            zone_dwell_times={"zone_apparel": 100000},
            has_joined_billing_queue=True,
            has_converted=True,
        ),
        # Session 2: Store entry (entries=4), Browsing Zones (engaged=3), Checkout (billing=2), No purchase
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_a9b1c2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 11, 40, tzinfo=timezone.utc),
            journey_path=["zone_electronics"],
            zone_dwell_times={"zone_electronics": 100000},
            has_joined_billing_queue=True,
            has_converted=False,
        ),
        # Session 3: Store entry (entries=4), Browsing Zones (engaged=3), No checkout, No purchase
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_d4e5f6",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 20, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 25, 0, tzinfo=timezone.utc),
            journey_path=["zone_electronics"],
            zone_dwell_times={"zone_electronics": 100000},
            has_joined_billing_queue=False,
            has_converted=False,
        ),
        # Session 4: Store entry (entries=4), No browsing zones (engaged=3), No checkout, No purchase
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_g7h8i9",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 30, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 31, 0, tzinfo=timezone.utc),
            journey_path=[],
            zone_dwell_times={},
            has_joined_billing_queue=False,
            has_converted=False,
        ),
    ]
    mock_session_repo.get_by_store_and_timerange.return_value = sessions

    res = await funnel_service.get_store_funnel("STORE_BLR_002")

    steps = res["steps"]
    
    # Step 1: Store Entry (4 entries, rate=100.0%)
    assert steps[0]["step_name"] == "Store Entry"
    assert steps[0]["visitor_count"] == 4
    assert steps[0]["conversion_rate"] == 100.0

    # Step 2: Browsing Zones (3 engaged, rate = 3 / 4 = 75.0%)
    assert steps[1]["step_name"] == "Browsing Zones"
    assert steps[1]["visitor_count"] == 3
    assert steps[1]["conversion_rate"] == 75.0

    # Step 3: Checkout Counter (2 billing, rate = 2 / 3 = 66.67%)
    assert steps[2]["step_name"] == "Checkout Counter"
    assert steps[2]["visitor_count"] == 2
    assert steps[2]["conversion_rate"] == 66.67

    # Step 4: Completed Purchase (1 purchase, rate = 1 / 2 = 50.0%)
    assert steps[3]["step_name"] == "Completed Purchase"
    assert steps[3]["visitor_count"] == 1
    assert steps[3]["conversion_rate"] == 50.0


@pytest.mark.asyncio
async def test_funnel_service_excludes_staff(funnel_service, mock_session_repo) -> None:
    """Verifies that sessions flagged as staff (is_staff=True) are completely excluded from calculated funnel steps."""
    sessions = [
        # Customer session: Store entry, Browsing Zones, Checkout, Converted
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_cust01",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc),
            journey_path=["zone_apparel"],
            zone_dwell_times={"zone_apparel": 100000},
            has_joined_billing_queue=True,
            has_converted=True,
            is_staff=False,
        ),
        # Staff session (should be completely omitted)
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_staff01",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            exited_at=datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
            journey_path=["zone_apparel"],
            zone_dwell_times={"zone_apparel": 200000},
            has_joined_billing_queue=True,
            has_converted=True,
            is_staff=True,
        ),
    ]
    mock_session_repo.get_by_store_and_timerange.return_value = sessions

    res = await funnel_service.get_store_funnel("STORE_BLR_002")

    steps = res["steps"]
    
    # Check that counts only reflect the single customer session
    assert steps[0]["visitor_count"] == 1
    assert steps[1]["visitor_count"] == 1
    assert steps[2]["visitor_count"] == 1
    assert steps[3]["visitor_count"] == 1
