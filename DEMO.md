# Replication & Demo Guide - DEMO.md

This guide provides the exact command sequence to start the database, execute migrations, run the computer vision pipeline on camera feeds, and query all analytics APIs.

---

## 1. Environment Setup

All commands must be executed in **PowerShell** from the project root folder `c:\Users\vaish\retail-intelligence`.

### Step 1: Active Python Environment
Ensure virtual environment is active and dependencies are installed:
```powershell
# Activate environment
.venv\Scripts\activate

# Confirm packages are installed
.venv\Scripts\python -m pip install -r requirements.txt
```

### Step 2: Spin Up Docker Database Container
Start the PostgreSQL database service in the background:
```powershell
docker compose up -d
```

### Step 3: Run Database Migrations
Execute Alembic migrations to set up the SQL schemas:
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

### Step 2: Run CV Detection, Stitching & Ingestion
Execute the automated verifier script. It runs YOLOv8 tracking on the camera videos, performs track stitching, ingests events to the database, hydrates sessions, and attributes POS transactions:
```powershell
$env:PYTHONPATH="."
.venv\Scripts\python pipeline/e2e_verifier.py
```
Wait for the CV runs on CAM1, CAM2, and CAM4 to complete. Once finished, it will display the output metrics summary in your terminal.

---

## 3. Querying REST Endpoints Manually

Verify database states and analytics by executing these `curl` commands in your terminal:

### A. Query Store Metrics
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/metrics
```

### B. Query Conversion Funnel Cohort
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/funnel
```

### C. Query Active Anomalies
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/anomalies
```

### D. Query Customer Journey Audits
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/journeys
```

### E. Query Cross-Camera Correlation Mappings
```powershell
curl http://127.0.0.1:8000/api/v1/stores/STORE_E2E_01/correlations
```
