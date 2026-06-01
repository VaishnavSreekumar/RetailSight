# Replication & Demo Guide

This guide provides the exact command sequence to start the database, execute migrations, load datasets, run the computer vision pipeline on camera feeds, and query all analytics APIs.

---

# Quick Start (60-Second Judge Path)

If you are a judge or reviewer looking for the fastest verification path, execute the following sequence:

### Step 1: Spin Up Containers
```powershell
docker compose up -d
```

### Step 2: Apply Database Schema Migrations
```powershell
$env:PYTHONPATH="."
.venv\Scripts\alembic upgrade head
```

### Step 3: Load Brigade POS Transaction Dataset
```powershell
.venv\Scripts\python data/load_brigade_transactions.py
```

### Step 4: Run E2E CCTV Validation Pipeline
This script runs YOLOv8 tracking on the real CCTV footage (`CCTV Footage/CAM 1.mp4`), generates telemetry events, ingests them into the database, and triggers session hydration:
```powershell
.venv\Scripts\python pipeline/run_cctv_validation.py
```

* **Expected Clean-Run Validation Results**:
  * Frames Processed: 4193
  * Events Generated: 355
  * Unique Visitors: 74
  * Sessions Hydrated: 74

### Step 5: Verify Analytics APIs
You can immediately query the root-level endpoints exposed directly for reviewer convenience:
```powershell
# 1. Retrieve visitor counts, conversion rate, and average session dwell time
curl http://127.0.0.1:8000/metrics

# 2. Retrieve CCTV shopper metrics matched against POS sales
curl http://127.0.0.1:8000/shopper-behavior

# 3. Retrieve section performance breakdown, top brands, and salesperson sales
curl http://127.0.0.1:8000/executive-dashboard
```

---

## 1. Environment Setup

All commands should be executed in **PowerShell** from the project root folder `c:\Users\vaish\retail-intelligence`.

### Step 1: Activate Python Environment & Install Dependencies
```powershell
# Activate environment
.venv\Scripts\activate

# Confirm packages are installed
.venv\Scripts\python -m pip install -r requirements.txt
```

### Step 2: Spin Up Docker Database Container
```powershell
docker compose up -d
```

### Step 3: Run Database Migrations
```powershell
$env:PYTHONPATH="."
.venv\Scripts\alembic upgrade head
```

---

## 2. API Server & Processing Pipeline

### Step 1: Start Backend API Server
Start the Uvicorn application server in a separate terminal:
```powershell
$env:PYTHONPATH="."
.venv\Scripts\uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```
Keep this server terminal running.

### Step 2: Populate Brigade Transaction Data
Run the loader script to populate the database with the real POS transactions from Brigade Road (ST1008):
```powershell
.venv\Scripts\python data/load_brigade_transactions.py
```
This script cleans the raw CSV, maps products to layout sections, and inserts them into the `brigade_transactions` table in PostgreSQL.

### Step 3: Run CCTV Video Validation
Run the real video validation pipeline to process coordinates, generate events, and hydrate visitor sessions:
```powershell
.venv\Scripts\python pipeline/run_cctv_validation.py
```
This will process the entire `CAM 1.mp4` video (4,193 frames) using YOLOv8 person tracking and register the shopper sessions.

---

## 3. Querying REST Endpoints Manually

Verify database states and analytics by executing these `curl` commands in your terminal:

### A. Root-Level Reviewer Endpoints (Direct & Convenient)
```powershell
# Query general store metrics (visitors, conversion rate)
curl http://127.0.0.1:8000/metrics

# Query shopper behavioral correlations (dwell time vs section sales)
curl http://127.0.0.1:8000/shopper-behavior

# Query executive dashboard layout analytics
curl http://127.0.0.1:8000/executive-dashboard
```

### B. Namespaced API Endpoint Details (`/api/v1/stores/...`)
If you want to query specific stores dynamically:
```powershell
# Query specific store metrics
curl http://127.0.0.1:8000/api/v1/stores/STORE_VAL_01/metrics

# Query conversion funnel cohort
curl http://127.0.0.1:8000/api/v1/stores/STORE_VAL_01/funnel

# Query active operational anomalies
curl http://127.0.0.1:8000/api/v1/stores/STORE_VAL_01/anomalies

# Query customer journey diagnostics
curl http://127.0.0.1:8000/api/v1/stores/STORE_VAL_01/journeys

# Query cross-camera correlation mappings
curl http://127.0.0.1:8000/api/v1/stores/STORE_VAL_01/correlations
```

---

## 4. Visual Layout & Analytics Screenshots

The validation pipeline output and dashboard responses can be visually reviewed using the screenshots stored under [docs/screenshots/](file:///c:/Users/vaish/retail-intelligence/docs/screenshots/):

* **Validation Run Execution**: [validation_run.png](file:///c:/Users/vaish/retail-intelligence/docs/screenshots/validation_run.png) shows the console output of the YOLOv8 validation script processing 4,193 frames.
* **Shopper Analytics Dashboard**: [val1.png](file:///c:/Users/vaish/retail-intelligence/docs/screenshots/val1.png) shows the shopper behavior correlation dashboard.
* **Executive Performance Dashboard**: [val2.png](file:///c:/Users/vaish/retail-intelligence/docs/screenshots/val2.png) shows layout section sales, ABV, and conversion trends.
