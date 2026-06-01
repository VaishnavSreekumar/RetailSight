# PROMPT: Build cross-camera tracking correlation tests to verify multi-camera visitor journeys.
# CHANGES MADE: Verified path stitching heuristics across camera streams based on exit/entry timeouts and physical store layout constraints.

from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from pipeline.correlation import VisitorCorrelationEngine, parse_track_id, normalize_camera_id
from app.services.correlation_diagnostics import CorrelationDiagnosticsService
from app.repositories.event_repository import EventRepository


def test_track_parsing_and_normalization() -> None:
    """Verifies helper track parsing and camera name normalization functions."""
    assert parse_track_id("VIS_003") == 3
    assert parse_track_id("VIS_G003") == 3
    assert parse_track_id("INVALID") == 0

    assert normalize_camera_id("CAM_ENTRY_01") == "CAM1"
    assert normalize_camera_id("CAM1") == "CAM1"
    assert normalize_camera_id("CAM_SKINCARE_01") == "CAM2"
    assert normalize_camera_id("CAM_BILLING_01") == "CAM4"


def test_correlation_engine_rules() -> None:
    """Verifies track correlation logic matches transitions and sets correct temporal confidences."""
    
    # Setup raw events
    base_time = datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc)
    
    events = [
        # Visitor A: enters CAM1 at t=0, exits CAM1 at t=5
        {"visitor_id": "VIS_002", "camera_id": "CAM_ENTRY_01", "event_type": "ENTRY", "timestamp": base_time.isoformat()},
        {"visitor_id": "VIS_002", "camera_id": "CAM_ENTRY_01", "event_type": "EXIT", "timestamp": (base_time + timedelta(seconds=5)).isoformat()},
        
        # Visitor A: enters CAM2 (Skincare) at t=10 (5s after CAM1 exit -> HIGH confidence)
        {"visitor_id": "VIS_002", "camera_id": "CAM_SKINCARE_01", "event_type": "ZONE_ENTER", "timestamp": (base_time + timedelta(seconds=10)).isoformat(), "zone_id": "SKINCARE"},
        {"visitor_id": "VIS_002", "camera_id": "CAM_SKINCARE_01", "event_type": "ZONE_EXIT", "timestamp": (base_time + timedelta(seconds=40)).isoformat(), "zone_id": "SKINCARE"},
        
        # Visitor B: enters CAM1 at t=10, exits CAM1 at t=12
        {"visitor_id": "VIS_003", "camera_id": "CAM_ENTRY_01", "event_type": "ENTRY", "timestamp": (base_time + timedelta(seconds=10)).isoformat()},
        {"visitor_id": "VIS_003", "camera_id": "CAM_ENTRY_01", "event_type": "EXIT", "timestamp": (base_time + timedelta(seconds=12)).isoformat()},

        # Visitor B: enters CAM2 (Skincare) at t=37 (25s after CAM1 exit -> LOW confidence)
        {"visitor_id": "VIS_003", "camera_id": "CAM_SKINCARE_01", "event_type": "ZONE_ENTER", "timestamp": (base_time + timedelta(seconds=37)).isoformat(), "zone_id": "SKINCARE"},

        # Visitor A: enters CAM4 (Billing) at t=65 (25s after CAM2 exit -> MEDIUM confidence)
        {"visitor_id": "VIS_002", "camera_id": "CAM_BILLING_01", "event_type": "BILLING_QUEUE_JOIN", "timestamp": (base_time + timedelta(seconds=65)).isoformat()},
    ]

    correlated_evts, registry = VisitorCorrelationEngine.correlate_events(events)

    # Visitor A track 2 should be mapped to the same global ID across CAM1, CAM2, CAM4
    g_id_a = registry.get_global_visitor("CAM1", 2)
    assert g_id_a is not None
    assert registry.get_global_visitor("CAM2", 2) == g_id_a
    assert registry.get_global_visitor("CAM4", 2) == g_id_a

    # Visitor B track 3 should be mapped to a separate global ID across CAM1, CAM2
    g_id_b = registry.get_global_visitor("CAM1", 3)
    assert g_id_b is not None
    assert g_id_b != g_id_a
    assert registry.get_global_visitor("CAM2", 3) == g_id_b

    # Verify confidences
    # Visitor A overall confidence should resolve to MEDIUM (lowest in its chain: HIGH entry, MEDIUM billing)
    assert registry.global_confidences[g_id_a] == "MEDIUM"
    
    # Visitor B confidence should resolve to LOW (transition dt=25s)
    assert registry.global_confidences[g_id_b] == "LOW"


def test_impossible_transitions() -> None:
    """Verifies that impossible topological paths (e.g. CAM4 -> CAM1 entry) do not correlate."""
    base_time = datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc)
    
    events = [
        # Visitor joins billing counter first (CAM4)
        {"visitor_id": "VIS_001", "camera_id": "CAM_BILLING_01", "event_type": "BILLING_QUEUE_JOIN", "timestamp": base_time.isoformat()},
        # Visitor enters store entryway 5 seconds later (CAM1) - impossible topology transition!
        {"visitor_id": "VIS_001", "camera_id": "CAM_ENTRY_01", "event_type": "ENTRY", "timestamp": (base_time + timedelta(seconds=5)).isoformat()},
    ]
    
    correlated_evts, registry = VisitorCorrelationEngine.correlate_events(events)
    
    g_id_4 = registry.get_global_visitor("CAM4", 1)
    g_id_1 = registry.get_global_visitor("CAM1", 1)
    
    # They must map to different global visitor IDs
    assert g_id_4 != g_id_1


@pytest.mark.asyncio
async def test_correlations_endpoint(client: AsyncClient, monkeypatch) -> None:
    """Verifies that the GET /stores/{store_id}/correlations endpoint returns correct schema payload."""
    store_id = "STORE_BLR_002"

    mock_corr_data = {
        "correlations": [
            {
                "global_visitor_id": "VIS_G001",
                "tracks": [
                    {"camera_id": "CAM1", "track_id": 2},
                    {"camera_id": "CAM2", "track_id": 2},
                ],
                "confidence": "HIGH"
            }
        ],
        "summary": {
            "total_global_visitors": 1,
            "total_track_fragments": 2,
            "average_tracks_per_visitor": 2.0
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

    monkeypatch.setattr(EventRepository, "get_all", lambda s: [])
    monkeypatch.setattr(CorrelationDiagnosticsService, "get_correlations", lambda e: mock_corr_data)

    from sqlalchemy.ext.asyncio import AsyncSession
    monkeypatch.setattr(AsyncSession, "execute", mock_execute)

    response = await client.get(f"/api/v1/stores/{store_id}/correlations")
    assert response.status_code == 200

    res_data = response.json()
    assert "correlations" in res_data
    assert "summary" in res_data
    assert len(res_data["correlations"]) == 1
    assert res_data["correlations"][0]["global_visitor_id"] == "VIS_G001"
    assert res_data["summary"]["total_global_visitors"] == 1
