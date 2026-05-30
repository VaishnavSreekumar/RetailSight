# E2E Demo Flow & Replication Guide

This guide walks you through replicating the complete **Retail Intelligence Platform** data flow:
$$\text{CCTV Video} \to \text{CV Tracking} \to \text{Cross-Camera Stitching} \to \text{Event Ingestion} \to \text{Session Hydration} \to \text{Transaction Linking} \to \text{Analytics APIs}$$

---

## 1. Prerequisites & Environment Setup

Ensure you are using PowerShell on Windows (or adjust syntax for Bash) and execute commands from the project root directory `c:\Users\vaish\retail-intelligence`.

### Step 1: Active Python Environment
Ensure dependencies are installed and the virtual environment is active:
```powershell
# Activate virtual environment
.venv\Scripts\activate

# Install requirements (if not done)
.venv\Scripts\python -m pip install -r requirements.txt
```

### Step 2: Spin Up PostgreSQL Database
Ensure the local database is running. If using Docker:
```powershell
docker-compose up -d
```
Check that the DB connection parameter matches `app/config.py`:
`postgresql+asyncpg://retail_user:retail_secure_password_2026@localhost:5432/retail_intelligence`

### Step 3: Run Database Migrations
Create database tables by running Alembic:
```powershell
$env:PYTHONPATH="."
.venv\Scripts\alembic upgrade head
```

---

## 2. Running the End-to-End Demo

The system provides a unified verification script, `pipeline/e2e_verifier.py`, that automates the entire flow.

### Step 1: Start Backend API Server
Start the Uvicorn server in a separate terminal window:
```powershell
$env:PYTHONPATH="."
.venv\Scripts\uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```
Keep this window open.

### Step 2: Launch the E2E Verifier
In your main terminal window, run the verifier script:
```powershell
$env:PYTHONPATH="."
.venv\Scripts\python pipeline/e2e_verifier.py
```

---

## 3. What Happens Under the Hood (Detailed Steps)

The verifier executes the following sequences, which can also be run or queried manually:

### 1. CV Detection and Tracking
Runs YOLOv8 object tracking (`yolov8n.pt` weight model) on raw MP4 video streams. Spatial boundaries are applied using zone coordinates.
* **CAM 1 (Entry/Exit)**: `CCTV Footage/CAM 1.mp4` $\to$ outputs `pipeline/output/e2e_cam1.jsonl`
* **CAM 2 (Skincare aisle)**: `CCTV Footage/CAM 2.mp4` $\to$ outputs `pipeline/output/e2e_cam2.jsonl`
* **CAM 4 (Billing counter)**: `CCTV Footage/CAM 4.mp4` $\to$ outputs `pipeline/output/e2e_cam4.jsonl`

### 2. Cross-Camera Correlation
Gathers events from all files and stitches tracks matching store transitions (e.g. `CAM1_TRACK_65` $\to$ `CAM2_TRACK_1` $\to$ `CAM4_TRACK_2`) into unified global visitor IDs (`VIS_G001`, `VIS_G002`, etc.) using the correlation heuristics in `pipeline/correlation.py`.

### 3. Event Ingestion API
Sends correlated events with embedded tracking metadata to the database:
```powershell
# Ingests payload of events
curl -X POST http://127.0.0.1:8000/api/v1/events/ingest `
  -H "Content-Type: application/json" `
  -d @pipeline/output/e2e_cam1.jsonl
```

### 4. Hydration and Transaction Linking
Reconstructs visitor sessions from event logs and matches them to a POS checkout log:
```powershell
# Hydrate and link POS transaction
curl -X POST http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/hydrate
```

---

## 4. Querying Analytics REST Endpoints

Verify the analytics deliverables using simple `curl` commands (or open them in a browser):

### 1. Shop Floor Performance Metrics
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/metrics
```
* **Returns**: Visitor counts, engaged browse percentage, conversion rate, average dwell time, average zones visited.

### 2. Customer Progression Funnel
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/funnel
```
* **Returns**: Stage-by-stage conversions: Entry $\to$ Browsing $\to$ Billing Queue $\to$ Purchased.

### 3. Anomaly and Operational Warnings
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/anomalies
```
* **Returns**: Alerts on excessive checkout queues or retail dead zones.

### 4. Customer Journey Audits
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/journeys
```
* **Returns**: Lists categorizing visitor cohorts: failed checkouts (queue but no purchase), pass-throughs (entry-exit only), and top-10 longest journeys.

### 5. Stitching Correlation Mappings
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/correlations
```
* **Returns**: Mappings from global visitor IDs to physical camera track IDs with confidence ratings.
