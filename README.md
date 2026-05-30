# Retail Intelligence Platform

An in-store customer analytics and tracking telemetry engine that converts multi-camera CCTV video feeds into structured visitor journeys,Attributes checkout receipts, and reports conversion metrics, funnel drop-offs, and operational anomalies.

---

## 1. Project Overview

Physical retail store managers have historically lacked the precise, cohort-level analytics available to e-commerce websites. This platform bridges that gap by using computer vision at the store edge to track visitor coordinates, debounces zone boundaries, stitches local tracks across camera streams, and matches checkouts to transactions in a central relational database.

---

## 2. System Architecture

The platform is divided into two decoupled subsystems:

### A. Edge Computer Vision Pipeline
* **YOLOv8 + ByteTrack**: Performs frame-by-frame person detection and tracking on local camera streams.
* **Zone Engine (Shapely)**: Evaluates bounding box coordinates against physical store region polygons (Entrance corridor, Skincare aisle, Checkout billing queue).
* **Correlation Engine**: Stitches local tracks across cameras using temporal and topological heuristics (Rules 1-4) to reconstruct global visitor paths.

### B. Cloud-Backend API Server
* **FastAPI Web Server**: Serves endpoints for event ingestion, session hydration, and analytics metrics.
* **PostgreSQL (JSONB)**: Stores events, transactions, and session paths. JSONB columns preserve semi-structured tracking metadata.
* **Transaction Matcher**: Attributes checkout transactions to visitor sessions based on queue-join indicators and time proximity.

For a detailed view of the system diagrams, refer to [DESIGN.md](./DESIGN.md) and [ADR.md](./ADR.md).

---

## 3. Quick Start & Replication

Ensure you are using **PowerShell** from the root folder `c:\Users\vaish\retail-intelligence`:

### Step 1: Active Python Environment
```powershell
.venv\Scripts\activate
.venv\Scripts\python -m pip install -r requirements.txt
```

### Step 2: Spin Up PostgreSQL Database Container
```powershell
docker compose up -d
```

### Step 3: Run Database Migrations
```powershell
$env:PYTHONPATH="."
.venv\Scripts\alembic upgrade head
```

### Step 4: Start Backend Application Server
In a separate terminal:
```powershell
$env:PYTHONPATH="."
.venv\Scripts\uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

### Step 5: Execute Automated Verification Runner
Processes 1000 video frames per camera, stitches tracks, runs event ingestion, database hydration, and prints store metrics:
```powershell
$env:PYTHONPATH="."
.venv\Scripts\python pipeline/e2e_verifier.py
```

---

## 4. API Overview

* **`POST /api/v1/events/ingest`**: Idempotent batch upload of camera tracking events.
* **`POST /api/v1/stores/{store_id}/hydrate`**: Group events by visitor, reconstruct sessions, and link POS transactions.
* **`GET /api/v1/stores/{store_id}/metrics`**: Retrieve store KPIs (traffic count, conversion rates, average browse dwell time).
* **`GET /api/v1/stores/{store_id}/funnel`**: Retrieve 4-stage cohort progression (Entry $\to$ Browse $\to$ Queue $\to$ Purchase).
* **`GET /api/v1/stores/{store_id}/anomalies`**: Retrieve active operations warnings (checkout queue spikes, dead zones).
* **`GET /api/v1/stores/{store_id}/journeys`**: Retrieve diagnostics journey audits (longest journeys, checkouts without purchases).
* **`GET /api/v1/stores/{store_id}/correlations`**: Retrieve camera track stitching diagnostics.

---

## 5. Testing Instructions

All unit and integration tests are located under the `tests/` directory. Run them using pytest:
```powershell
.venv\Scripts\python -m pytest
```
* **Output**: All 46 tests pass successfully.

---

## 6. Screenshots & Visualizations

*(Placeholders for future frontend integration)*
* **Overview Analytics**: Visualizes total foot traffic, conversion trend curves, and active store alerts.
* **Spatial Dwell Heatmaps**: SVG polygons representing the skincare aisle, entry corridor, and checkout counter overlaid directly onto static camera snapshots. Color scales (Cool blue to Warm red) indicate visitor dwell averages.

---

## 7. Known Limitations & Future Enhancements

* **Deterministic Cross-Camera Correlation**:
  * *Limitation*: Can confuse different tracks if multiple exits and entrances occur inside the same 5-second window.
  * *Enhancement*: Implement a hybrid correlation engine that extracts lightweight person clothing embedding descriptors (using OSNet) to resolve temporal collisions.
* **Transaction Attribution Order Swaps**:
  * *Limitation*: Greedy proximity matching can swap attribution if checkouts occur in rapid succession.
  * *Enhancement*: Incorporate cashier camera object recognition to track what items are in the customer's hands at the register and match item list contents directly to the transaction SKU array.
* **Static Anomaly Thresholds**:
  * *Limitation*: Static limits (e.g. 120s queue spike alert) do not scale well during holiday peak periods.
  * *Enhancement*: Train an adaptive seasonal baseline model (Holt-Winters or Prophet) to evaluate alerts dynamically.
