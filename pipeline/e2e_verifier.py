import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Add project root to sys.path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

from pipeline.runner import run_pipeline
from app.config import settings
from app.models.transaction import Transaction

BACKEND_URL = "http://127.0.0.1:8000/api/v1"
STORE_ID = "STORE_E2E_01"


async def insert_mock_transaction(timestamp: datetime):
    """Inserts a mock transaction directly into the database for E2E linking."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        # Delete any existing transaction for safety
        from sqlalchemy import delete
        await session.execute(delete(Transaction).filter(Transaction.store_id == STORE_ID))
        
        # Insert a new transaction occurring shortly after entry (e.g. +10 seconds)
        txn = Transaction(
            id="TXN_E2E_001",
            store_id=STORE_ID,
            timestamp=timestamp + timedelta(seconds=10),
            total_amount=129.99,
            payment_method="UPI",
            items=[{"sku": "SKU_SKINCARE_01", "quantity": 1, "price": 129.99}]
        )
        session.add(txn)
        await session.commit()
        print(f"Inserted mock POS transaction {txn.id} in DB.")
    await engine.dispose()


async def verify_e2e():
    print("=== STARTING END-TO-END VERIFICATION ===")

    # 1. Run the CV pipeline on three different cameras (100 frames each for speed)
    print("\n--- 1. Running CV Pipeline on CCTV Footage ---")
    
    # Ensure output directories exist
    Path("pipeline/output").mkdir(parents=True, exist_ok=True)
    
    cam1_video = "CCTV Footage/CAM 1.mp4"
    cam2_video = "CCTV Footage/CAM 2.mp4"
    cam4_video = "CCTV Footage/CAM 4.mp4"
    
    if not (os.path.exists(cam1_video) and os.path.exists(cam2_video) and os.path.exists(cam4_video)):
        print("Error: CCTV video files not found in 'CCTV Footage/' directory.")
        return

    print("Processing CAM 1 (Entry/Exit)...")
    run_pipeline(
        video_path=cam1_video,
        output_path="pipeline/output/e2e_cam1.jsonl",
        store_id=STORE_ID,
        camera_id="CAM_ENTRY_01",
        max_frames=1000,
        config_path="pipeline/sample_store_config/zones_cam1.json"
    )

    print("Processing CAM 2 (Skincare aisle)...")
    run_pipeline(
        video_path=cam2_video,
        output_path="pipeline/output/e2e_cam2.jsonl",
        store_id=STORE_ID,
        camera_id="CAM_SKINCARE_01",
        max_frames=1000,
        config_path="pipeline/sample_store_config/zones_cam2.json"
    )

    print("Processing CAM 4 (Billing counter)...")
    run_pipeline(
        video_path=cam4_video,
        output_path="pipeline/output/e2e_cam4.jsonl",
        store_id=STORE_ID,
        camera_id="CAM_BILLING_01",
        max_frames=1000,
        config_path="pipeline/sample_store_config/zones_cam4.json"
    )

    # 2. Gather and combine generated events
    print("\n--- 2. Combining & Correlating Generated Events ---")
    raw_events = []
    earliest_timestamp = None
    
    for filename in ["e2e_cam1.jsonl", "e2e_cam2.jsonl", "e2e_cam4.jsonl"]:
        filepath = Path("pipeline/output") / filename
        if filepath.exists():
            with open(filepath, "r") as f:
                for line in f:
                    if line.strip():
                        evt = json.loads(line)
                        raw_events.append(evt)
                        
                        # Track earliest timestamp for mock transaction matching
                        ts = datetime.fromisoformat(evt["timestamp"])
                        if earliest_timestamp is None or ts < earliest_timestamp:
                            earliest_timestamp = ts

    print(f"Total raw events gathered: {len(raw_events)}")
    if not raw_events:
        print("No events generated. Aborting E2E run.")
        return

    # Run Cross-Camera Visitor Correlation
    from pipeline.correlation import VisitorCorrelationEngine
    events, registry = VisitorCorrelationEngine.correlate_events(raw_events)
    
    print("\n--- Correlation Engine Metrics ---")
    print(f"Total Global Visitors Registered: {len(registry.global_to_tracks)}")
    print(f"Total Local Tracks Mapped: {len(registry.track_to_global)}")
    for g_id, tracks in sorted(registry.global_to_tracks.items()):
        track_strings = [f"{t['camera_id']}_TRACK_{t['track_id']}" for t in tracks]
        conf = registry.global_confidences.get(g_id, "HIGH")
        print(f"  {g_id} (Confidence: {conf}) -> {', '.join(track_strings)}")

    # 3. Ingest events into the backend
    print("\n--- 3. Ingesting Events into Backend API ---")
    async with httpx.AsyncClient() as client:
        payload = {"events": events}
        resp = await client.post(f"{BACKEND_URL}/events/ingest", json=payload)
        if resp.status_code != 201:
            print(f"Failed to ingest events: {resp.status_code} - {resp.text}")
            return
        
        ingest_res = resp.json()
        print(f"Ingestion response: {ingest_res}")

    # 4. Insert mock POS transaction
    print("\n--- 4. Inserting Mock POS Transaction ---")
    await insert_mock_transaction(earliest_timestamp or datetime.now(timezone.utc))

    # 5. Trigger Session Hydration and Linking
    print("\n--- 5. Triggering Session Hydration & Transaction Linking ---")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/stores/{STORE_ID}/hydrate")
        if resp.status_code != 200:
            print(f"Failed to hydrate sessions: {resp.status_code} - {resp.text}")
            return
        
        hydrate_res = resp.json()
        print(f"Hydration response: {hydrate_res}")

    # 6. Fetch Analytics Results
    print("\n--- 6. Retrieving Analytics and Audits ---")
    async with httpx.AsyncClient() as client:
        # Get metrics
        m_resp = await client.get(f"{BACKEND_URL}/stores/{STORE_ID}/metrics")
        print(f"Store Metrics: {json.dumps(m_resp.json(), indent=2)}")
        
        # Get funnel
        f_resp = await client.get(f"{BACKEND_URL}/stores/{STORE_ID}/funnel")
        print(f"Store Funnel: {json.dumps(f_resp.json(), indent=2)}")
        
        # Get anomalies
        a_resp = await client.get(f"{BACKEND_URL}/stores/{STORE_ID}/anomalies")
        print(f"Store Anomalies: {json.dumps(a_resp.json(), indent=2)}")

        # Get transaction matches diagnostics
        tm_resp = await client.get(f"{BACKEND_URL}/stores/{STORE_ID}/transaction-matches")
        print(f"Transaction Matches Diagnostics: {json.dumps(tm_resp.json(), indent=2)}")

        # Get customer journey diagnostics & audit
        j_resp = await client.get(f"{BACKEND_URL}/stores/{STORE_ID}/journeys")
        j_data = j_resp.json()
        print("\n--- Journey Audit Summary ---")
        print(f"Total Reconstructed Journeys: {len(j_data['journeys'])}")
        print(f"Longest Journeys (Top 10): {len(j_data['audit']['longest_journeys'])}")
        print(f"Failed Checkouts (Billing Queue, No Purchase): {len(j_data['audit']['billing_queue_no_purchase'])}")
        print(f"Purchases with No Retail Zones: {len(j_data['audit']['purchase_no_retail_zones'])}")
        print(f"Entry-Exit Only (Pass-through / Noise): {len(j_data['audit']['entry_exit_only'])}")
        print(f"Single Zone Sessions: {len(j_data['audit']['single_zone_sessions'])}")
        print("\nDetailed Journey Audit Data:")
        print(json.dumps(j_data["audit"], indent=2))

        # Get correlations diagnostics
        c_resp = await client.get(f"{BACKEND_URL}/stores/{STORE_ID}/correlations")
        print(f"\nStore Correlations Diagnostics: {json.dumps(c_resp.json(), indent=2)}")

    print("\n=== E2E VERIFICATION COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    # Ensure Uvicorn server is running locally on port 8000
    asyncio.run(verify_e2e())
