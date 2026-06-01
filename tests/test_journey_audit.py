# PROMPT: Develop validation harness for visitor journey diagnostics and detailed E2E telemetry logging.
# CHANGES MADE: Verified chronological track stitching consistency and complete transaction history audits for single store visits.

from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from app.services.journey_audit_service import JourneyAuditService
from app.repositories.session_repository import SessionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.event_repository import EventRepository


def test_journey_audit_service_categories() -> None:
    """Verifies that JourneyAuditService correctly maps, calculates durations, and filters audit segments."""
    
    # 1. Prepare raw events mapping to visitor journeys
    events = [
        # Session 1 events (skincare visit, then checkout join)
        {"visitor_id": "v1", "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc), "event_type": "ENTRY"},
        {"visitor_id": "v1", "timestamp": datetime(2026, 5, 30, 10, 1, 0, tzinfo=timezone.utc), "event_type": "ZONE_ENTER", "zone_id": "SKINCARE"},
        {"visitor_id": "v1", "timestamp": datetime(2026, 5, 30, 10, 2, 0, tzinfo=timezone.utc), "event_type": "BILLING_QUEUE_JOIN"},
        {"visitor_id": "v1", "timestamp": datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc), "event_type": "EXIT"},
        
        # Session 2 events (skincare visit, no checkout queue)
        {"visitor_id": "v2", "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc), "event_type": "ENTRY"},
        {"visitor_id": "v2", "timestamp": datetime(2026, 5, 30, 10, 1, 0, tzinfo=timezone.utc), "event_type": "ZONE_ENTER", "zone_id": "SKINCARE"},
        {"visitor_id": "v2", "timestamp": datetime(2026, 5, 30, 10, 2, 0, tzinfo=timezone.utc), "event_type": "EXIT"},
        
        # Session 3 events (no zones visited, direct checkout join)
        {"visitor_id": "v3", "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc), "event_type": "ENTRY"},
        {"visitor_id": "v3", "timestamp": datetime(2026, 5, 30, 10, 1, 0, tzinfo=timezone.utc), "event_type": "BILLING_QUEUE_JOIN"},
        {"visitor_id": "v3", "timestamp": datetime(2026, 5, 30, 10, 3, 0, tzinfo=timezone.utc), "event_type": "EXIT"},

        # Session 4 events (entry/exit only)
        {"visitor_id": "v4", "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc), "event_type": "ENTRY"},
        {"visitor_id": "v4", "timestamp": datetime(2026, 5, 30, 10, 1, 0, tzinfo=timezone.utc), "event_type": "EXIT"},
    ]

    # 2. Prepare hydrated session objects
    sessions = [
        # Session 1: Dwell = 5 mins, joined billing, has purchase (linked)
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "visitor_id": "v1",
            "journey_path": ["SKINCARE"],
            "entered_at": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            "exited_at": datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc),
            "has_joined_billing_queue": True,
            "associated_txn_id": "txn_01",
        },
        # Session 2: Dwell = 2 mins, single zone skincare, no purchase
        {
            "id": "00000000-0000-0000-0000-000000000002",
            "visitor_id": "v2",
            "journey_path": ["SKINCARE"],
            "entered_at": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            "exited_at": datetime(2026, 5, 30, 10, 2, 0, tzinfo=timezone.utc),
            "has_joined_billing_queue": False,
            "associated_txn_id": None,
        },
        # Session 3: Dwell = 3 mins, joined queue, has purchase, but NO retail zones browsed
        {
            "id": "00000000-0000-0000-0000-000000000003",
            "visitor_id": "v3",
            "journey_path": [],
            "entered_at": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            "exited_at": datetime(2026, 5, 30, 10, 3, 0, tzinfo=timezone.utc),
            "has_joined_billing_queue": True,
            "associated_txn_id": "txn_03",
        },
        # Session 4: Dwell = 1 min, no zones, no purchase (Entry/Exit only)
        {
            "id": "00000000-0000-0000-0000-000000000004",
            "visitor_id": "v4",
            "journey_path": [],
            "entered_at": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            "exited_at": datetime(2026, 5, 30, 10, 1, 0, tzinfo=timezone.utc),
            "has_joined_billing_queue": False,
            "associated_txn_id": None,
        },
        # Session 5: Dwell = 4 mins, joined queue but NO purchase (failed checkout)
        {
            "id": "00000000-0000-0000-0000-000000000005",
            "visitor_id": "v1", # same visitor re-entering
            "journey_path": ["SKINCARE"],
            "entered_at": datetime(2026, 5, 30, 11, 0, 0, tzinfo=timezone.utc),
            "exited_at": datetime(2026, 5, 30, 11, 4, 0, tzinfo=timezone.utc),
            "has_joined_billing_queue": True,
            "associated_txn_id": None,
        }
    ]

    # 3. Prepare transactions
    transactions = [
        {"id": "txn_01", "total_amount": 100.0, "timestamp": datetime(2026, 5, 30, 10, 6, 0, tzinfo=timezone.utc)},
        {"id": "txn_03", "total_amount": 50.0, "timestamp": datetime(2026, 5, 30, 10, 4, 0, tzinfo=timezone.utc)},
    ]

    result = JourneyAuditService.audit_cohort(sessions, transactions, events)

    # 4. Perform assertion checks
    # Total journeys parsed: 5
    assert len(result["journeys"]) == 5
    
    # Event count mapping: Session 1 has 4 events
    s1_parsed = next(j for j in result["journeys"] if j["session_id"] == "00000000-0000-0000-0000-000000000001")
    assert s1_parsed["event_count"] == 4
    assert s1_parsed["session_duration_ms"] == 5.0 * 60.0 * 1000.0 # 300,000 ms
    assert s1_parsed["associated_transaction"]["transaction_id"] == "txn_01"

    # Category checks
    # Longest journeys sorting check (Session 1 is 5 mins, Session 5 is 4 mins)
    longest = result["audit"]["longest_journeys"]
    assert longest[0]["session_id"] == "00000000-0000-0000-0000-000000000001"
    assert longest[1]["session_id"] == "00000000-0000-0000-0000-000000000005"

    # Billing queue but no purchase: Session 5 only (since session 1 & 3 have purchase)
    bq_no_pur = result["audit"]["billing_queue_no_purchase"]
    assert len(bq_no_pur) == 1
    assert bq_no_pur[0]["session_id"] == "00000000-0000-0000-0000-000000000005"

    # Purchase with no retail zones: Session 3 (associated_txn_id=txn_03, journey_path=[])
    pur_no_zone = result["audit"]["purchase_no_retail_zones"]
    assert len(pur_no_zone) == 1
    assert pur_no_zone[0]["session_id"] == "00000000-0000-0000-0000-000000000003"

    # Entry-Exit only: Session 4 (not in queue, no zones, no purchase)
    ee_only = result["audit"]["entry_exit_only"]
    assert len(ee_only) == 1
    assert ee_only[0]["session_id"] == "00000000-0000-0000-0000-000000000004"

    # Single Zone Sessions: Session 1, Session 2, and Session 5 (all have exactly one retail zone ["SKINCARE"])
    single_zone = result["audit"]["single_zone_sessions"]
    assert len(single_zone) == 3
    single_zone_ids = [s["session_id"] for s in single_zone]
    assert "00000000-0000-0000-0000-000000000001" in single_zone_ids
    assert "00000000-0000-0000-0000-000000000002" in single_zone_ids
    assert "00000000-0000-0000-0000-000000000005" in single_zone_ids


@pytest.mark.asyncio
async def test_journeys_endpoint(client: AsyncClient, monkeypatch) -> None:
    """Verifies that the GET /stores/{store_id}/journeys API returns correctly parsed payload."""
    store_id = "STORE_BLR_002"

    mock_audit_data = {
        "journeys": [
            {
                "session_id": "00000000-0000-0000-0000-000000000001",
                "visitor_id": "v1",
                "journey_path": ["SKINCARE"],
                "entered_at": "2026-05-30T10:00:00Z",
                "exited_at": "2026-05-30T10:05:00Z",
                "zones_visited": ["SKINCARE"],
                "joined_billing_queue": True,
                "associated_transaction": {
                    "transaction_id": "txn_01",
                    "timestamp": "2026-05-30T10:06:00Z",
                    "total_amount": 100.0,
                },
                "event_count": 4,
                "session_duration_ms": 300000.0,
            }
        ],
        "audit": {
            "longest_journeys": [],
            "billing_queue_no_purchase": [],
            "purchase_no_retail_zones": [],
            "entry_exit_only": [],
            "single_zone_sessions": [],
        }
    }

    async def mock_execute(*args, **kwargs):
        class MockResult:
            def scalars(self):
                class MockScalars:
                    def all(self):
                        return []
                return MockScalars()
        return MockResult()

    async def mock_get_by_store(*args, **kwargs):
        return []

    # Monkeypatch repository data retrievals
    monkeypatch.setattr(SessionRepository, "get_by_store", mock_get_by_store)
    monkeypatch.setattr(TransactionRepository, "get_by_store", mock_get_by_store)
    
    # Mock JourneyAuditService.audit_cohort
    monkeypatch.setattr(JourneyAuditService, "audit_cohort", lambda s, t, e: mock_audit_data)

    # We also mock the sqlalchemy execute call in the endpoint
    from sqlalchemy.ext.asyncio import AsyncSession
    monkeypatch.setattr(AsyncSession, "execute", mock_execute)

    response = await client.get(f"/api/v1/stores/{store_id}/journeys")
    assert response.status_code == 200

    res_data = response.json()
    assert "journeys" in res_data
    assert "audit" in res_data
    assert len(res_data["journeys"]) == 1
    assert res_data["journeys"][0]["visitor_id"] == "v1"
    assert res_data["journeys"][0]["event_count"] == 4
    assert res_data["journeys"][0]["session_duration_ms"] == 300000.0
