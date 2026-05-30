# Engineering Decisions & Design Choices - CHOICES.md

This document details the core architectural and technology choices made during the development of the **Retail Intelligence Platform**, highlighting the options considered, decisions taken, tradeoffs, and future pathways.

---

## 1. Object Detection Model: YOLOv8

* **Problem**: Extracting real-time bounding boxes of persons moving through store cameras at high FPS and high accuracy.
* **Options Considered**:
  * **Option A**: YOLOv5 (Established baseline, but lower accuracy-to-latency ratio).
  * **Option B**: YOLOv8 (SOTA single-stage detector, native support for PyTorch/ONNX, class-specific filtering).
  * **Option C**: Faster R-CNN (Highly accurate, but too slow for edge-based real-time 30 FPS processing).
* **Decision**: **YOLOv8 (specifically `yolov8n.pt` Nano weight)**.
* **Tradeoffs**: YOLOv8 Nano uses less memory (6MB weight file) and runs extremely fast on CPU/GPU. However, it can experience small bounding box jitter under high occlusion (e.g., people standing close in skincare aisles).
* **Future Improvements**: Calibrate and quantize YOLOv8 to TensorRT or ONNX Runtime to run on edge accelerators.

---

## 2. Tracking Framework: Built-in ByteTrack

* **Problem**: Maintaining unique track IDs for visitors across contiguous video frames in a single camera view.
* **Options Considered**:
  * **Option A**: OpenCV Centroid Tracker (Simple, but fails under bounding box overlap and occlusions).
  * **Option B**: ByteTrack / BoTSORT (Native tracking algorithms in Ultralytics YOLOv8 library. ByteTrack tracks low-score boxes to maintain tracks through occlusions).
  * **Option C**: Custom Kalman Filter Tracker (High dev overhead to write from scratch).
* **Decision**: **ByteTrack** (invoked natively via `model.track(persist=True, tracker="bytetrack.yaml")`).
* **Tradeoffs**: ByteTrack maintains tracking continuity exceptionally well, but tracker ID swaps can still occur if a person is fully occluded for more than 30 frames.
* **Future Improvements**: Tweak matching metrics (IOU weights and track buffer sizes) inside `bytetrack.yaml` to match the specific camera height and angles of the store layout.

---

## 3. Cross-Camera Visitor Correlation

* **Problem**: Track disappearance on a camera stream terminates that track, fragmenting a single physical journey into disjointed pieces.
* **Options Considered**:
  * **Option A**: Deep Learning Re-ID (e.g. Torchreid, OSNet embeddings). Matches features extracted from clothing.
  * **Option B**: Heuristic-based Correlation Engine (using transition times, store layout topology, and temporal proximity).
* **Decision**: **Heuristic-based Correlation Engine (`VisitorCorrelationEngine`)**.
* **Tradeoffs**: Bypasses heavy feature extraction networks, meaning the pipeline executes in milliseconds on simple CPUs. However, if two different people enter CAM2 within a 5-second window after exiting CAM1, the engine will greedily match the closest timestamp, potentially causing a ID mismatch.
* **Future Improvements**: Implement a hybrid engine that uses fast heuristics first, falling back to a lightweight Re-ID embedding model only for temporal collisions under 10 seconds.

---

## 4. Session Hydration Architecture

* **Problem**: Converting time-series camera events into persistent `VisitorSession` records.
* **Options Considered**:
  * **Option A**: Hydration on Ingestion (`/events/ingest` endpoint hydrates sessions synchronously).
  * **Option B**: Decoupled Hydration Service (Ingestion endpoint ONLY writes events; session hydration `/hydrate` is triggered separately or asynchronously).
* **Decision**: **Decoupled Hydration Service (`SessionHydrationService`)**.
* **Tradeoffs**: Separates concerns. If ingestion receives 500 events, it doesn't block the request on database reads, session reconstruction, and transaction matching. The tradeoff is that the client must trigger hydration separately.
* **Future Improvements**: Move hydration to an asynchronous worker queue (e.g. Celery / Redis) triggered automatically on event insertion.

---

## 5. POS Transaction Matching Strategy

* **Problem**: Correlating credit-card or digital checkout POS logs to physical visitor tracks without utilizing biometric data.
* **Options Considered**:
  * **Option A**: Basic Proximity Match (link the closest transaction to any session exiting the store entryway).
  * **Option B**: Queue-Aware Temporal Proximity (link transactions based on billing queue join/dwell timestamps and transaction times).
* **Decision**: **Queue-Aware Temporal Proximity (`TransactionMatcher`)**.
* **Tradeoffs**: Highly effective because it requires the session to have registered `has_joined_billing_queue == True` and applies time-decay score penalties if the transaction timestamp differs from the queue dwell window. However, it cannot link cash purchases if multiple buyers checkout simultaneously and checkout order swaps occur.
* **Future Improvements**: Incorporate order list mapping: match the items in the customer's hands (detected via CV) to the items on the POS receipt to resolve checkout order swaps.

---

## 6. Anomaly Engine Alert Strategy

* **Problem**: Detecting operational errors (long queues, dead zones, conversion dropouts) dynamically.
* **Options Considered**:
  * **Option A**: Standard Static Thresholds (alerts trigger if any single metric breaches a hardcoded limit).
  * **Option B**: Time-series historical baselines (alerts trigger if current store performance deviates significantly from historical averages).
* **Decision**: **Hybrid Anomaly Engine** (uses static thresholds for queue wait times, and comparison against historical averages for conversion drops).
* **Tradeoffs**: Easy to configure and interpret. However, static queue thresholds (e.g., 2 minutes) might be acceptable during holiday peak periods but problematic during off-peak hours.
* **Future Improvements**: Feed metrics into a statistical anomalies model (e.g., Holt-Winters seasonal baseline) to evaluate thresholds dynamically.

---

## 7. Storage Choice: PostgreSQL

* **Problem**: Persisting raw video telemetry events and structured visitor session journeys.
* **Options Considered**:
  * **Option A**: MongoDB / NoSQL (Flexible schema, but lacks ACID compliance for transactional POS data).
  * **Option B**: In-Memory Redis (Fast, but lacks persistence).
  * **Option C**: PostgreSQL (ACID compliance, relational mapping, and robust JSONB support for unstructured telemetry coordinates).
* **Decision**: **PostgreSQL (utilizing native JSONB column fields)**.
* **Tradeoffs**: Provides SQL relations for linking sessions and POS transactions while retaining NoSQL flexibility by saving unstructured camera details and coordinates inside the `metadata` JSONB column.
* **Future Improvements**: Implement TimescaleDB extension on PostgreSQL to optimize the query speed of raw event timelines.

---

## 8. Web Framework: FastAPI

* **Problem**: Serving high-concurrency REST endpoints for store analytics and ingestion.
* **Options Considered**:
  * **Option A**: Django (Comprehensive, but heavy and slower async execution).
  * **Option B**: Flask (Lightweight, but lacks native async and Pydantic validation).
  * **Option C**: FastAPI (High performance, async/await native, automatic OpenAPI documentation, and strict Pydantic parsing).
* **Decision**: **FastAPI**.
* **Tradeoffs**: Ingestion and metrics calculation endpoints run with sub-millisecond latencies. The tradeoff is the need to write custom database manager configurations compared to Django's built-in ORM.
* **Future Improvements**: Enable Gunicorn as a process manager to run multiple FastAPI worker processes on multi-core servers.

---

## 9. Containerization: Docker & Docker Compose

* **Problem**: Packaging the application stack (FastAPI web server, PostgreSQL database) to ensure identical, repeatable reviewer execution.
* **Options Considered**:
  * **Option A**: Direct local environment installations (risk of Python/Library version mismatches).
  * **Option B**: Docker & Docker Compose (Containerized isolation of FastAPI and PostgreSQL).
* **Decision**: **Docker & Docker Compose**.
* **Tradeoffs**: Isolates database configurations and Python version requirements. The tradeoff is that running the computer vision pipeline inside the container is slower if it lacks access to the host GPU.
* **Future Improvements**: Configure the Dockerfile to pass NVIDIA GPU drivers through to the container to accelerate PyTorch YOLOv8 tracking runs.
