from datetime import datetime, timezone

from app.services.session_hydrator import SessionHydrator


def test_normal_customer_journey() -> None:
    """Validates that a normal customer journey maps entered times, zones, and dwells."""
    events = [
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            "is_staff": False,
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "ZONE_ENTER",
            "zone_id": "zone_groceries",
            "timestamp": datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "ZONE_DWELL",
            "zone_id": "zone_groceries",
            "dwell_ms": 120000,
            "timestamp": datetime(2026, 5, 30, 10, 7, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 10, 15, 0, tzinfo=timezone.utc),
        },
    ]

    sessions = SessionHydrator.hydrate_sessions(events)
    assert len(sessions) == 1
    session = sessions[0]

    assert session.visitor_id == "VIS_c8a2f1"
    assert session.store_id == "STORE_BLR_002"
    assert session.entered_at == datetime(
        2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc
    )
    assert session.exited_at == datetime(
        2026, 5, 30, 10, 15, 0, tzinfo=timezone.utc
    )
    assert session.journey_path == ["zone_groceries"]
    assert session.zone_dwell_times == {"zone_groceries": 120000}
    assert session.is_staff is False
    assert session.has_joined_billing_queue is False


def test_customer_exits_immediately() -> None:
    """Validates that a customer exiting immediately records correct times and empty paths."""
    events = [
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            "is_staff": False,
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 10, 0, 5, tzinfo=timezone.utc),
        },
    ]

    sessions = SessionHydrator.hydrate_sessions(events)
    assert len(sessions) == 1
    session = sessions[0]

    assert session.entered_at == datetime(
        2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc
    )
    assert session.exited_at == datetime(
        2026, 5, 30, 10, 0, 5, tzinfo=timezone.utc
    )
    assert session.journey_path == []
    assert session.zone_dwell_times == {}


def test_reentry_flow() -> None:
    """Validates that a visitor reentering a store generates two separate tracking sessions."""
    events = [
        # Session 1
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
        },
        # Session 2
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "REENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 20, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "ZONE_ENTER",
            "zone_id": "zone_apparel",
            "timestamp": datetime(2026, 5, 30, 10, 22, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 10, 30, 0, tzinfo=timezone.utc),
        },
    ]

    sessions = SessionHydrator.hydrate_sessions(events)
    assert len(sessions) == 2
    s1, s2 = sessions

    assert s1.entered_at == datetime(
        2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc
    )
    assert s1.exited_at == datetime(
        2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc
    )
    assert s1.journey_path == []

    assert s2.entered_at == datetime(
        2026, 5, 30, 10, 20, 0, tzinfo=timezone.utc
    )
    assert s2.exited_at == datetime(
        2026, 5, 30, 10, 30, 0, tzinfo=timezone.utc
    )
    assert s2.journey_path == ["zone_apparel"]


def test_staff_session() -> None:
    """Validates that entries marked as staff retain staff attributes in completed sessions."""
    events = [
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 9, 0, 0, tzinfo=timezone.utc),
            "is_staff": True,
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 17, 0, 0, tzinfo=timezone.utc),
        },
    ]

    sessions = SessionHydrator.hydrate_sessions(events)
    assert len(sessions) == 1
    session = sessions[0]

    assert session.is_staff is True


def test_billing_queue_join() -> None:
    """Validates that a billing queue join event flags the session's queue parameter correctly."""
    events = [
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "BILLING_QUEUE_JOIN",
            "timestamp": datetime(2026, 5, 30, 10, 12, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_c8a2f1",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 10, 18, 0, tzinfo=timezone.utc),
        },
    ]

    sessions = SessionHydrator.hydrate_sessions(events)
    assert len(sessions) == 1
    session = sessions[0]

    assert session.has_joined_billing_queue is True


def test_exact_duplicate_event_filtering() -> None:
    """Validates that exact identical events in the input stream are filtered out."""
    events = [
        {
            "visitor_id": "VIS_dup001",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
        },
        # Exact duplicate
        {
            "visitor_id": "VIS_dup001",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_dup001",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
        },
    ]
    sessions = SessionHydrator.hydrate_sessions(events)
    assert len(sessions) == 1
    assert sessions[0].entered_at == datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc)
    assert sessions[0].exited_at == datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc)


def test_consecutive_duplicate_entry_deduplication() -> None:
    """Validates that consecutive ENTRY events are ignored/deduplicated."""
    events = [
        {
            "visitor_id": "VIS_dup002",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_dup002",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 0, 5, tzinfo=timezone.utc),  # Consecutive duplicate
        },
        {
            "visitor_id": "VIS_dup002",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
        },
    ]
    sessions = SessionHydrator.hydrate_sessions(events)
    assert len(sessions) == 1
    assert sessions[0].entered_at == datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc)


def test_consecutive_duplicate_zone_enter_deduplication() -> None:
    """Validates that consecutive ZONE_ENTER events for the same zone are ignored/deduplicated."""
    events = [
        {
            "visitor_id": "VIS_dup003",
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_dup003",
            "store_id": "STORE_BLR_002",
            "event_type": "ZONE_ENTER",
            "zone_id": "zone_apparel",
            "timestamp": datetime(2026, 5, 30, 10, 2, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_dup003",
            "store_id": "STORE_BLR_002",
            "event_type": "ZONE_ENTER",
            "zone_id": "zone_apparel",
            "timestamp": datetime(2026, 5, 30, 10, 3, 0, tzinfo=timezone.utc),  # Consecutive duplicate
        },
        {
            "visitor_id": "VIS_dup003",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
        },
    ]
    sessions = SessionHydrator.hydrate_sessions(events)
    assert len(sessions) == 1
    assert sessions[0].journey_path == ["zone_apparel"]


def test_ghost_session_prevention() -> None:
    """Validates that sessions are not initialized on stray ZONE_DWELL or EXIT events."""
    events = [
        {
            "visitor_id": "VIS_ghost",
            "store_id": "STORE_BLR_002",
            "event_type": "ZONE_DWELL",
            "zone_id": "zone_groceries",
            "dwell_ms": 5000,
            "timestamp": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
        },
        {
            "visitor_id": "VIS_ghost",
            "store_id": "STORE_BLR_002",
            "event_type": "EXIT",
            "timestamp": datetime(2026, 5, 30, 10, 5, 0, tzinfo=timezone.utc),
        },
    ]
    sessions = SessionHydrator.hydrate_sessions(events)
    assert len(sessions) == 0

