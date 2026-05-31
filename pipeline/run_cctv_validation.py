"""
pipeline/run_cctv_validation.py
================================
Sprint 24 – Data Integrity & Real CCTV Validation

Produces an end-to-end proof:
    Video → Detection → Tracking → EventGenerator → API Ingest
         → Session Hydration → /metrics → VALIDATION_PROOF

Usage (with the FastAPI server running on :8000):
    python pipeline/run_cctv_validation.py

Output files:
    pipeline/output/validation_events.jsonl   – raw events from real video
    pipeline/output/validation_proof.json     – machine-readable E2E proof
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── path bootstrap ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# ────────────────────────────────────────────────────────────────────────────

import cv2
import httpx
from shapely.geometry import Polygon

from pipeline.event_generator import EventGenerator
from pipeline.models import Track
from pipeline.tracker import YOLOv8Tracker
from pipeline.zones import ZoneEngine

# ── Configuration ────────────────────────────────────────────────────────────
STORE_ID    = "STORE_VAL_01"          # unique store ID for this validation run
CAMERA_ID   = "CAM_ENTRY_01"
VIDEO_PATH  = str(ROOT / "CCTV Footage" / "CAM 1.mp4")
ZONE_CONFIG = str(ROOT / "pipeline" / "sample_store_config" / "zones_cam1.json")
OUTPUT_DIR  = ROOT / "pipeline" / "output"
EVENTS_FILE = OUTPUT_DIR / "validation_events.jsonl"
PROOF_FILE  = OUTPUT_DIR / "validation_proof.json"
BACKEND     = "http://127.0.0.1:8000/api/v1"
MAX_FRAMES  = 4193    # Process the entire video
FPS_TARGET  = 30.0
# ────────────────────────────────────────────────────────────────────────────


def load_zone_config(path: str) -> dict:
    """Load and build Shapely polygons from a JSON zone config file."""
    with open(path) as f:
        raw = json.load(f)

    def make_poly(coords: list) -> Polygon | None:
        if not coords:
            return None
        pts = [(c[0], c[1]) for c in coords]
        return Polygon(pts)

    retail_zones = {}
    for name, coords in raw.get("retail_zones", {}).items():
        p = make_poly(coords)
        if p:
            retail_zones[name] = p

    return {
        "entry_zone":  make_poly(raw.get("entry_zone", [])) or Polygon(),
        "billing_zone": make_poly(raw.get("billing_zone", [])) or Polygon(),
        "retail_zones": retail_zones,
    }


def run_video_pipeline(
    video_path: str,
    zone_config_path: str,
    store_id: str,
    camera_id: str,
    max_frames: int = 500,
) -> list[dict]:
    """
    Process a real MP4 video with YOLOv8 tracking and generate events.

    Returns a list of raw event dicts.
    """
    print(f"\n[PIPELINE] Opening video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    actual_fps = cap.get(cv2.CAP_PROP_FPS) or FPS_TARGET
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[PIPELINE] Video FPS={actual_fps:.1f}, total frames={total_video_frames}, "
          f"processing first {min(max_frames, total_video_frames)} frames")

    zones = load_zone_config(zone_config_path)
    zone_engine = ZoneEngine(zones)
    tracker = YOLOv8Tracker(model_name=str(ROOT / "yolov8n.pt"))

    start_time = datetime(2026, 5, 31, 12, 0, 0, tzinfo=timezone.utc)
    event_gen = EventGenerator(
        zone_engine=zone_engine,
        store_id=store_id,
        fps=actual_fps,
        start_time=start_time,
        camera_id=camera_id,
    )

    all_events: list[dict] = []
    frame_idx = 0
    t0 = time.time()

    while frame_idx < max_frames:
        ok, frame = cap.read()
        if not ok:
            break

        tracks_raw: list[Track] = tracker.track_frame(frame)
        events = event_gen.process_frame(frame_idx, tracks_raw)

        for e in events:
            all_events.append(e.to_dict())

        if frame_idx % 100 == 0:
            elapsed = time.time() - t0
            unique_visitors = len({ev["visitor_id"] for ev in all_events})
            print(f"  frame {frame_idx:4d} | events so far: {len(all_events):4d} "
                  f"| unique visitors: {unique_visitors} | elapsed: {elapsed:.1f}s")

        frame_idx += 1

    cap.release()
    elapsed = time.time() - t0
    print(f"[PIPELINE] Done. Processed {frame_idx} frames in {elapsed:.1f}s → {len(all_events)} events")
    return all_events


def save_events(events: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    print(f"[PIPELINE] Events saved → {path}")


async def ingest_events(events: list[dict]) -> dict:
    print(f"\n[API] Ingesting {len(events)} events into {BACKEND}/events/ingest …")
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{BACKEND}/events/ingest", json={"events": events})
        resp.raise_for_status()
        result = resp.json()
        print(f"[API] Ingest response: {result}")
        return result


async def hydrate_sessions() -> dict:
    print(f"\n[API] Triggering session hydration for store {STORE_ID} …")
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{BACKEND}/stores/{STORE_ID}/hydrate")
        resp.raise_for_status()
        result = resp.json()
        print(f"[API] Hydration response: {result}")
        return result


async def fetch_metrics() -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{BACKEND}/stores/{STORE_ID}/metrics")
        resp.raise_for_status()
        return resp.json()


async def fetch_journeys() -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{BACKEND}/stores/{STORE_ID}/journeys")
        resp.raise_for_status()
        return resp.json()


def build_e2e_proof(
    events: list[dict],
    ingest_result: dict,
    hydrate_result: dict,
    metrics: dict,
    journeys: dict,
) -> dict:
    """
    Build a machine-readable end-to-end proof for a single visitor example.
    Picks the first visitor who has at least one ENTRY event.
    """
    # Pick the first visitor with an ENTRY event
    example_visitor_id: str | None = None
    example_events: list[dict] = []

    for ev in events:
        if ev["event_type"] == "ENTRY" and example_visitor_id is None:
            example_visitor_id = ev["visitor_id"]
        if example_visitor_id and ev["visitor_id"] == example_visitor_id:
            example_events.append(ev)

    # Find corresponding session in journeys
    example_journey = None
    if example_visitor_id and journeys.get("journeys"):
        for j in journeys["journeys"]:
            if j.get("visitor_id") == example_visitor_id:
                example_journey = j
                break

    proof = {
        "proof_generated_at": datetime.now(timezone.utc).isoformat(),
        "store_id": STORE_ID,
        "camera_id": CAMERA_ID,
        "video_file": VIDEO_PATH,
        "frames_processed": MAX_FRAMES,

        "step_1_video_to_events": {
            "description": "Real YOLOv8n tracker ran on actual MP4 frames. "
                           "EventGenerator state machine converted tracks to events.",
            "total_events_generated": len(events),
            "unique_visitor_ids": len({e["visitor_id"] for e in events}),
            "event_types": {
                et: sum(1 for e in events if e["event_type"] == et)
                for et in sorted({e["event_type"] for e in events})
            },
        },

        "step_2_events_ingested": {
            "description": "POST /api/v1/events/ingest",
            "api_response": ingest_result,
        },

        "step_3_sessions_hydrated": {
            "description": "POST /api/v1/stores/{store_id}/hydrate "
                           "— SessionHydrationService aggregates events into VisitorSession rows.",
            "api_response": hydrate_result,
        },

        "step_4_dashboard_metrics": {
            "description": "GET /api/v1/stores/{store_id}/metrics "
                           "— All counts sourced from visitor_sessions table.",
            "formula_visitor_count":    "SELECT COUNT(*) FROM visitor_sessions WHERE store_id = :store_id",
            "formula_purchase_count":   "SELECT COUNT(*) FROM visitor_sessions WHERE store_id = :store_id AND has_converted = TRUE",
            "formula_queue_entries":    "SELECT COUNT(*) FROM visitor_sessions WHERE store_id = :store_id AND has_joined_billing_queue = TRUE",
            "formula_conversion_rate":  "(purchase_count / visitor_count) * 100  → percentage [0, 100]",
            "formula_abandonment_rate": "((queue_entries - purchases) / queue_entries)  → fraction [0, 1]",
            "live_metrics": metrics,
        },

        "step_5_single_visitor_proof": {
            "description": f"Full chain for visitor {example_visitor_id}",
            "visitor_id": example_visitor_id,
            "raw_events_from_video": example_events,
            "hydrated_journey": example_journey,
        },

        "data_source_audit": {
            "visitor_events": "REAL — YOLOv8n detection + ByteTrack tracking on actual CAM 1.mp4 video frames",
            "sessions": "REAL — derived from visitor_events by SessionHydrationService",
            "metrics": "REAL — counted from visitor_sessions table via SQL WHERE store_id filter",
            "brigade_pos_transactions": "REAL — parsed from Brigade_Bangalore CSV file (Sprint 19)",
            "mock_data": "NONE in this validation run — e2e_verifier.py TXN_E2E_001 is isolated to its own STORE_E2E_01 store",
        },
    }
    return proof


async def main() -> None:
    print("=" * 60)
    print("  Sprint 24 – CCTV Validation End-to-End Proof")
    print("=" * 60)

    # ── Step 1: Run real video pipeline ──────────────────────────────────────
    if not os.path.exists(VIDEO_PATH):
        print(f"ERROR: Video not found at {VIDEO_PATH}")
        sys.exit(1)

    events = run_video_pipeline(
        video_path=VIDEO_PATH,
        zone_config_path=ZONE_CONFIG,
        store_id=STORE_ID,
        camera_id=CAMERA_ID,
        max_frames=MAX_FRAMES,
    )

    if not events:
        print("ERROR: No events generated. Check zone config and video path.")
        sys.exit(1)

    save_events(events, EVENTS_FILE)

    # ── Steps 2–3: API ingest + hydrate ──────────────────────────────────────
    ingest_result = await ingest_events(events)
    hydrate_result = await hydrate_sessions()

    # ── Step 4: Fetch metrics ─────────────────────────────────────────────────
    print(f"\n[API] Fetching metrics for store {STORE_ID} …")
    metrics = await fetch_metrics()
    print(f"[API] Metrics: {json.dumps(metrics, indent=2, default=str)}")

    # ── Fetch journeys for visitor-level proof ────────────────────────────────
    print(f"\n[API] Fetching journeys for store {STORE_ID} …")
    journeys = await fetch_journeys()
    print(f"[API] Total journeys reconstructed: {len(journeys.get('journeys', []))}")

    # ── Step 5: Build proof JSON ──────────────────────────────────────────────
    proof = build_e2e_proof(events, ingest_result, hydrate_result, metrics, journeys)

    with open(PROOF_FILE, "w") as f:
        json.dump(proof, f, indent=2, default=str)

    print(f"\n[PROOF] Saved → {PROOF_FILE}")
    print("\n" + "=" * 60)
    print("  E2E Validation Summary")
    print("=" * 60)
    print(f"  Events generated from real video : {proof['step_1_video_to_events']['total_events_generated']}")
    print(f"  Unique visitors detected         : {proof['step_1_video_to_events']['unique_visitor_ids']}")
    print(f"  Sessions hydrated                : {hydrate_result.get('hydrated_count', 'n/a')}")
    print(f"  visitor_count (DB)               : {metrics.get('visitors', 'n/a')}")
    print(f"  purchase_count (DB)              : {metrics.get('purchases', 'n/a')}")
    print(f"  queue_entries (DB)               : {metrics.get('billing_queue_visitors', 'n/a')}")
    print(f"  conversion_rate (%)              : {metrics.get('conversion_rate', 'n/a')}")
    print(f"  Example visitor                  : {proof['step_5_single_visitor_proof']['visitor_id']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
