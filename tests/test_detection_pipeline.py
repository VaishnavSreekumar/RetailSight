from datetime import datetime, timezone
import pytest
from shapely.geometry import Polygon

from pipeline.event_generator import EventGenerator
from pipeline.models import Track
from pipeline.zones import ZoneEngine


def test_zone_engine_polygon_containment() -> None:
    """Verifies that the ZoneEngine correctly identifies when tracked visitor coordinate is inside/outside polygons."""
    # Define simple unit square zones
    zones = {
        "entry_zone": Polygon([[0, 0], [2, 0], [2, 2], [0, 2]]),
        "billing_zone": Polygon([[8, 8], [10, 8], [10, 10], [8, 10]]),
        "retail_zones": {"SKINCARE": Polygon([[4, 4], [6, 4], [6, 6], [4, 6]])},
    }

    engine = ZoneEngine(zones)

    # Bottom-center is (1.0, 1.0) -> inside entry_zone
    t_entry = Track(track_id=1, bbox=(0.5, 0.5, 1.5, 1.0), confidence=0.9)
    assert engine.is_in_entry(t_entry) is True
    assert engine.is_in_billing(t_entry) is False
    assert engine.get_retail_zone(t_entry) is None

    # Bottom-center is (5.0, 5.0) -> inside SKINCARE
    t_skincare = Track(track_id=2, bbox=(4.0, 4.0, 6.0, 5.0), confidence=0.85)
    assert engine.is_in_entry(t_skincare) is False
    assert engine.get_retail_zone(t_skincare) == "SKINCARE"


def test_event_generator_state_machine() -> None:
    """Verifies event generation lifecycle (ENTRY, transitions, debouncing, periodic dwell, and exit timeouts)."""
    zones = {
        "entry_zone": Polygon([[0, 0], [2, 0], [2, 2], [0, 2]]),
        "billing_zone": Polygon([[8, 8], [10, 8], [10, 10], [8, 10]]),
        "retail_zones": {
            "SKINCARE": Polygon([[4, 4], [6, 4], [6, 6], [4, 6]]),
            "MAKEUP": Polygon([[14, 14], [16, 14], [16, 16], [14, 16]]),
        },
    }

    engine = ZoneEngine(zones)
    store_id = "STORE_BLR_002"

    # Setup generator: 30 FPS, exit timeout 3 frames, zone debounce 2 frames, min dwell 1 second (30 frames)
    generator = EventGenerator(
        zone_engine=engine,
        store_id=store_id,
        fps=30.0,
        start_time=datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
        exit_timeout_frames=3,
        zone_debounce_frames=2,
        min_dwell_seconds=1.0,
    )

    # Track 1 at Entry
    t_entry = Track(track_id=1, bbox=(0.5, 0.5, 1.5, 1.0), confidence=0.9)

    # Frame 0: first frame track 1 seen at Entry -> should trigger ENTRY event
    events = generator.process_frame(0, [t_entry])
    assert len(events) == 1
    assert events[0].event_type == "ENTRY"
    assert events[0].visitor_id == "VIS_001"

    # Frame 1: track 1 stays in Entry -> no events (already entered)
    events = generator.process_frame(1, [t_entry])
    assert len(events) == 0

    # Track moves to SKINCARE zone
    t_skincare = Track(track_id=1, bbox=(4.0, 4.0, 6.0, 5.0), confidence=0.95)

    # Frame 2: enters Skincare -> candidate zone is Skincare, consecutive frames = 1. No event emitted yet (debouncing)
    events = generator.process_frame(2, [t_skincare])
    assert len(events) == 0

    # Frame 3: stays in Skincare -> consecutive frames = 2 >= debounce (2). Trigger ZONE_ENTER event
    events = generator.process_frame(3, [t_skincare])
    assert len(events) == 1
    assert events[0].event_type == "ZONE_ENTER"
    assert events[0].zone_id == "SKINCARE"
    # Visitor average confidence includes track 1's frames confidences
    assert events[0].confidence == 0.925  # (0.9 + 0.9 + 0.95 + 0.95) / 4 = 0.925

    # Stays in skincare for 30 frames (1 second) to test periodic dwell
    # Frame 3 to 33 -> 30 frames (1.0 second elapsed). Emits periodic ZONE_DWELL at frame 33
    for f in range(4, 33):
        events = generator.process_frame(f, [t_skincare])
        assert len(events) == 0

    events = generator.process_frame(33, [t_skincare])
    assert len(events) == 1
    assert events[0].event_type == "ZONE_DWELL"
    assert events[0].zone_id == "SKINCARE"
    assert events[0].dwell_ms == 1000

    # Track moves to MAKEUP zone
    t_makeup = Track(track_id=1, bbox=(14.0, 14.0, 16.0, 15.0), confidence=0.9)

    # Frame 34: candidate MAKEUP (1 frame)
    events = generator.process_frame(34, [t_makeup])
    assert len(events) == 0

    # Frame 35: consecutive = 2 >= 2 -> exits SKINCARE (ZONE_EXIT + ZONE_DWELL) and enters MAKEUP (ZONE_ENTER)
    events = generator.process_frame(35, [t_makeup])
    assert len(events) == 3
    types = [e.event_type for e in events]
    assert "ZONE_EXIT" in types
    assert "ZONE_DWELL" in types
    assert "ZONE_ENTER" in types

    dwell_event = [e for e in events if e.event_type == "ZONE_DWELL"][0]
    assert dwell_event.zone_id == "SKINCARE"
    # Dwell from last emission (frame 33) to exit (frame 35) is 2 frames -> 2 / 30 = 66.6ms
    assert 50 <= dwell_event.dwell_ms <= 80

    # Track moves to Billing
    t_billing = Track(track_id=1, bbox=(8.5, 8.5, 9.5, 9.0), confidence=0.9)

    # Frame 36: joins billing -> BILLING_QUEUE_JOIN
    events = generator.process_frame(36, [t_billing])
    assert len(events) == 1
    assert events[0].event_type == "BILLING_QUEUE_JOIN"

    # Track disappears
    # Frame 37: track not seen (last seen 36) -> no events
    events = generator.process_frame(37, [])
    assert len(events) == 0

    # Frame 38: track not seen (last seen 36) -> difference is 2 < 3 -> no events
    events = generator.process_frame(38, [])
    assert len(events) == 0

    # Frame 39: track not seen (last seen 36) -> difference is 3 >= 3 -> triggers exit (ZONE_EXIT + ZONE_DWELL + EXIT)
    events = generator.process_frame(39, [])
    assert len(events) == 3
    types = [e.event_type for e in events]
    assert "ZONE_EXIT" in types
    assert "ZONE_DWELL" in types
    assert "EXIT" in types
