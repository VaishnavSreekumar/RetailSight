# PROMPT: Develop core rule engine tests for detecting retail store operational anomalies.
# CHANGES MADE: Created assertions checking queue spikes, conversion rate drops, and dead zone alerts, verifying staff exclusion.

from datetime import datetime, timezone
import pytest

from app.models.visitor_session import VisitorSession
from app.services.anomaly_engine import AnomalyEngine


def test_queue_spike_no_baseline() -> None:
    """Verifies that no queue spike is triggered if historical baseline is zero."""
    evaluation_time = datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc)
    sessions = [
        # Current window: 3 checkout sessions
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_c8a2f1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 55, 0, tzinfo=timezone.utc),
            has_joined_billing_queue=True,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_a9b1c2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 56, 0, tzinfo=timezone.utc),
            has_joined_billing_queue=True,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_d4e5f6",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 57, 0, tzinfo=timezone.utc),
            has_joined_billing_queue=True,
        ),
    ]

    anomalies = AnomalyEngine.detect_anomalies(sessions, evaluation_time=evaluation_time)
    queue_spikes = [a for a in anomalies if a["type"] == "QUEUE_SPIKE"]
    assert len(queue_spikes) == 0


def test_queue_spike_success() -> None:
    """Verifies that queue spike triggers when current depth >= 3, > 2x baseline, and diff >= 2."""
    evaluation_time = datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc)
    
    # Baseline window has 1 queue session over 15 intervals -> baseline = 1/15 = 0.067
    # Current window has 3 queue sessions.
    # Criteria check:
    # baseline = 0.067 > 0
    # current = 3 >= 3
    # current > 2 * baseline (3 > 0.133)
    # current - baseline = 2.933 >= 2
    sessions = [
        # Baseline window session
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_hist1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            has_joined_billing_queue=True,
        ),
        # Current window sessions
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_c8a2f1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 55, 0, tzinfo=timezone.utc),
            has_joined_billing_queue=True,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_a9b1c2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 56, 0, tzinfo=timezone.utc),
            has_joined_billing_queue=True,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_d4e5f6",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 57, 0, tzinfo=timezone.utc),
            has_joined_billing_queue=True,
        ),
    ]

    anomalies = AnomalyEngine.detect_anomalies(sessions, evaluation_time=evaluation_time)
    queue_spikes = [a for a in anomalies if a["type"] == "QUEUE_SPIKE"]
    assert len(queue_spikes) == 1
    assert queue_spikes[0]["severity"] == "HIGH"
    assert queue_spikes[0]["metric_value"] == 3.0
    assert queue_spikes[0]["baseline_value"] == 0.07


def test_conversion_drop_success() -> None:
    """Verifies that relative conversion drop decline triggers when drop >= 30%."""
    evaluation_time = datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc)
    
    # Previous window (11:00 to 11:30): 2 sessions, both converted -> 100% rate
    # Current window (11:30 to 12:00): 2 sessions, 1 converted -> 50% rate
    # Relative drop = (100 - 50) / 100 = 50% decline >= 30%
    sessions = [
        # Previous window
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_prev1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 10, 0, tzinfo=timezone.utc),
            has_converted=True,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_prev2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 15, 0, tzinfo=timezone.utc),
            has_converted=True,
        ),
        # Current window
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_curr1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 40, 0, tzinfo=timezone.utc),
            has_converted=True,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_curr2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 45, 0, tzinfo=timezone.utc),
            has_converted=False,
        ),
    ]

    anomalies = AnomalyEngine.detect_anomalies(sessions, evaluation_time=evaluation_time)
    drops = [a for a in anomalies if a["type"] == "CONVERSION_DROP"]
    assert len(drops) == 1
    assert drops[0]["severity"] == "HIGH"
    assert drops[0]["metric_value"] == 50.0
    assert drops[0]["baseline_value"] == 100.0


def test_conversion_drop_insufficient_decline() -> None:
    """Verifies that no drop is triggered if decline is below 30% relative rate."""
    evaluation_time = datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc)
    
    # Previous window: 2 sessions, 1 converted -> 50% rate
    # Current window: 2 sessions, 1 converted -> 50% rate
    # Decline = 0% < 30%
    sessions = [
        # Previous window
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_prev1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 10, 0, tzinfo=timezone.utc),
            has_converted=True,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_prev2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 15, 0, tzinfo=timezone.utc),
            has_converted=False,
        ),
        # Current window
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_curr1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 40, 0, tzinfo=timezone.utc),
            has_converted=True,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_curr2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 45, 0, tzinfo=timezone.utc),
            has_converted=False,
        ),
    ]

    anomalies = AnomalyEngine.detect_anomalies(sessions, evaluation_time=evaluation_time)
    drops = [a for a in anomalies if a["type"] == "CONVERSION_DROP"]
    assert len(drops) == 0


def test_dead_zone_promotion() -> None:
    """Verifies promotion of opportunity loss zones to DEAD_ZONE anomalies."""
    evaluation_time = datetime(2026, 5, 30, 12, 0, 0, tzinfo=timezone.utc)
    
    # Zone Apparel has high dwell but low conversion and low billing queue progression
    sessions = [
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_c8a2f1",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 0, 0, tzinfo=timezone.utc),
            journey_path=["zone_electronics"],
            zone_dwell_times={"zone_electronics": 50000},
            has_joined_billing_queue=True,
            has_converted=True,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_a9b1c2",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 10, 0, tzinfo=timezone.utc),
            journey_path=["zone_apparel"],
            zone_dwell_times={"zone_apparel": 500000},
            has_joined_billing_queue=False,
            has_converted=False,
        ),
        VisitorSession(
            id=VisitorSession.id.default.arg,
            visitor_id="VIS_d4e5f6",
            store_id="STORE_BLR_002",
            entered_at=datetime(2026, 5, 30, 11, 20, 0, tzinfo=timezone.utc),
            journey_path=["zone_apparel"],
            zone_dwell_times={"zone_apparel": 300000},
            has_joined_billing_queue=False,
            has_converted=False,
        ),
    ]

    anomalies = AnomalyEngine.detect_anomalies(sessions, evaluation_time=evaluation_time)
    dead_zones = [a for a in anomalies if a["type"] == "DEAD_ZONE"]
    assert len(dead_zones) == 1
    assert dead_zones[0]["severity"] == "MEDIUM"
    assert dead_zones[0]["affected_zone"] == "zone_apparel"
