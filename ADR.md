# Architecture Decision Records (ADRs)

This document maps the major architectural decisions of the **Retail Intelligence Platform** using the industry-standard ADR template.

---

## ADR-001: Object Detection Framework (YOLOv8)

### Status
Accepted

### Context
The platform requires a real-time computer vision detection framework to locate customers on video frames. The detector must run on generic CPU nodes without GPU requirements, maintaining a minimum processing frame rate of 10-15 FPS.

### Decision
We chose **YOLOv8 (specifically the `yolov8n.pt` Nano weight variant)**. It combines single-stage bounding box extraction and class identification in a single network pass, optimized for fast latency.

### Consequences
* Runs at high FPS (20+ FPS on generic CPUs).
* Small model size (6.2 MB) allows packaging within edge docker containers.
* Bounding boxes can occasionally jitter under heavy occlusion.

---

## ADR-002: Visitor Tracking Subsystem (ByteTrack)

### Status
Accepted

### Context
Maintaining track identity within a single camera's field of view is required to measure zone dwell times and sequence paths.

### Decision
We chose **ByteTrack** (invoked natively via the Ultralytics tracker package). It is a tracking-by-detection algorithm that leverages association scores on both high-confidence and low-confidence boxes to maintain tracks during brief occlusions.

### Consequences
* Highly stable track preservation under overlapping visitor paths.
* Zero external code integration cost.
* Occlusion windows exceeding 30 frames will still trigger track swaps.

---

## ADR-003: Cross-Camera Track Stitching (Heuristics)

### Status
Accepted

### Context
To reconstruct complete visitor store sessions, camera-local track segments must be stitched into global visitor profiles (e.g. mapping entrance track to skincare browsing track).

### Decision
We chose **Deterministic Heuristics (time-delta transitions and store topology rules)** rather than deep learning Re-ID feature embeddings.

### Consequences
* Correlation runs in sub-milliseconds on CPU.
* Avoids high-latency feature extraction and spatial-temporal vector space math.
* High traffic densities (crowds) can cause temporal matching conflicts when multiple tracks trigger exit/enter events inside the same time window.

---

## ADR-004: Decoupled Session Hydration

### Status
Accepted

### Context
Unstructured time-series telemetry events arrive at the backend in batches. These events must be parsed and aggregated into structured customer sessions.

### Decision
We separated session hydration (`POST /hydrate`) from event ingestion (`POST /events/ingest`). The ingestion route solely performs fast validation and writes to the DB; hydration compiles session tables later.

### Consequences
* Bulk event ingestion remains sub-millisecond and highly responsive.
* Prevents blocking API responses on complex database reads and transaction matching operations.
* The client must trigger hydration separately or setup a background task.

---

## ADR-005: Backend Framework (FastAPI)

### Status
Accepted

### Context
The platform requires a high-performance, asynchronous REST backend to handle batch event uploads and serve real-time analytics dashboards.

### Decision
We chose **FastAPI**. It leverages ASGI and Starlette for high concurrency and async execution, using Pydantic for data validation.

### Consequences
* Extremely fast response rates (sub-5ms on standard endpoints).
* Automatic, interactive OpenAPI documentation (`/docs`).
* Higher boilerplate compared to Django for complex database setups.

---

## ADR-006: Database Storage (PostgreSQL with JSONB)

### Status
Accepted

### Context
The platform stores structured relational entities (POS transactions, customer sessions) alongside semi-structured, telemetry metadata (original coordinates, confidence).

### Decision
We chose **PostgreSQL with JSONB columns**.

### Consequences
* Maintains transactional consistency (ACID) for Point-of-Sale data and session links.
* Retains NoSQL flexibility by allowing unstructured details (original tracking metadata) to be queried directly from JSONB fields.
* Minor query overhead when searching deeply nested JSON structures.
