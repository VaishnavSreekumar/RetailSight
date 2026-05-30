# Platform Architecture Documentation

This document describes the architectural layout of the **Retail Intelligence Platform**, separating the edge-based **Computer Vision Detection Pipeline** from the cloud-based **Backend Analytics Pipeline**.

---

## 1. Detection Pipeline (Computer Vision Edge)

The computer vision pipeline processes CCTV footage frame-by-frame, performs tracking, maps coordinates to retail zone polygons, and correlates tracks across cameras to produce stitched, global retail events.

```mermaid
graph TD
    %% Source
    A[CCTV Video Streams <br> CAM 1, CAM 2, CAM 4] -->|Frame Stream| B[Runner <br> runner.py]

    %% Tracking Layer
    subgraph Tracking & Detection
        B --> C[YOLOv8 Tracker <br> tracker.py]
        C -->|Person Class detections| D[ByteTrack Tracker]
        D -->|Unique Track IDs & Bbox coords| E[Track Entity]
    end

    %% Spatial Mapping Layer
    subgraph Spatial & Temporal Zone Mapping
        E --> F[Zone Engine <br> zones.py]
        G[Zone Configurations <br> Shapely Polygons] --> F
        F -->|Bbox Bottom-Center Mapping| H[Active Zone State]
    end

    %% Event Extraction
    subgraph Event Extraction & Debouncing
        H --> I[Event Generator <br> event_generator.py]
        I -->|Debounce Zone Enter/Exit| J[Filtered Local Events]
        I -->|30-frame Disappearance Timeout| K[Local Exit Events]
    end

    %% Correlation Layer
    subgraph Track Stitching Heuristics
        J & K --> L[Visitor Correlation Engine <br> correlation.py]
        M[Global Visitor Registry] <--> L
        L -->|Stitch local camera tracks <br> Apply topology & closest match| N[Global Correlated Events]
    end

    %% Output
    N -->|Save file| O[JSONL Event Files <br> e.g. e2e_cam1.jsonl]
```

### Components:
* **YOLOv8 & ByteTrack**: Fast, edge-based object tracking. Maps pixel coordinates of visitors and tracks them across frames.
* **Zone Engine (Shapely)**: Translates bounding box bottom-center coordinates into logical regions (Skincare aisle, Entry/Exit corridor, Billing counter queue) using geometric intersection.
* **Event Generator State Machine**: Bypasses frame noise by requiring a visitor to dwell inside a polygon for 10 frames before entering, and emits exits after 30 consecutive frames of track loss.
* **Visitor Correlation Engine**: Runs post-processing track stitching. Links tracks from CAM1 exit to CAM2 entry, and CAM2 aisle to CAM4 billing counter. Enforces store topology limits (no backtracking like CAM4 -> CAM1).

---

## 2. Backend Pipeline (Hydration, Storage & APIs)

The backend ingestion pipeline receives correlated events, stores them, aggregates them into customer sessions, attributes POS transactions, and exposes analytic API routes.

```mermaid
graph TD
    %% Ingestion
    A[JSONL Global Events] -->|POST /events/ingest| B[Ingest Route <br> events.py]
    
    %% Storage
    subgraph Database Layer
        B -->|Idempotent bulk insert| C[(PostgreSQL Database)]
        C <--> D[events table <br> JSONB metadata column]
        C <--> E[visitor_sessions table]
        C <--> F[transactions table]
    end

    %% Hydration Service
    subgraph Session Hydration & Matching
        G[POST /stores/store_id/hydrate] --> H[Session Hydration Service]
        H <-->|Fetch raw events| D
        H -->|Reconstruct chronologies| I[Visitor Session Entities]
        I -->|Persist session states| E

        %% Transaction Linking
        H <-->|Match transaction times & queue| J[Transaction Matcher]
        J <-->|Fetch POS records| F
        J -->|Update session link: associated_txn_id| E
    end

    %% API Endpoints
    subgraph REST API Endpoints
        E & D --> K[GET /stores/store_id/metrics] -->|StoreMetrics Schema| K_Out[Analytics Dashboard]
        E --> L[GET /stores/store_id/funnel] -->|FunnelReport Schema| L_Out[Conversion Funnel]
        E --> M[GET /stores/store_id/anomalies] -->|AnomalyResponse Schema| M_Out[Operations Alerts]
        E & F & D --> N[GET /stores/store_id/journeys] -->|JourneyResponse Schema| N_Out[Journeys Diagnostic Audit]
        D --> O[GET /stores/store_id/correlations] -->|CorrelationDiagnosticsResponse| O_Out[Stitching Performance]
    end
```

### Components:
* **JSONB Metadata Persistence**: Preserves the original `track_id`, `camera_id`, and `correlation_confidence` directly in the events record, bypassing database schema updates.
* **Session Hydration Service**: Batches individual enter/dwell/exit events into unified visitor session records (e.g. VIS_G001 visited entry $\to$ skincare $\to$ billing counter).
* **Transaction Matcher**: Resolves session-transaction pairs. Scores matches based on timestamps and queue presence.
* **Analytics/Diagnostics API Engine**: Converts sessions and transactions into actionable store intelligence (metrics, conversion rates, queue warnings, and journey cohort analysis).
