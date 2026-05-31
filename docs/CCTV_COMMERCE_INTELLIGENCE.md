# CCTV Commerce Intelligence

This document explains how the platform connects CCTV-derived shopper behavior with Point-of-Sale (POS) commerce data to generate actionable business insights.

## Data Flow: From Pixels to Profits

The core of this intelligence lies in a multi-stage data enrichment pipeline that transforms raw video into business KPIs.

### 1. CCTV Telemetry (The `pipeline` directory)

-   **Source**: Raw CCTV video feeds.
-   **Process**: The computer vision pipeline detects and tracks individuals, generating a stream of `(visitor_id, camera_id, x, y, timestamp)` coordinates.
-   **Output**: Raw tracking data.

### 2. Event Generation (`events` table)

-   **Source**: Raw tracking data and `cctv_zones.json`.
-   **Process**: The system compares visitor coordinates against predefined geometric zones (e.g., "SKINCARE_WALL", "CHECKOUT_QUEUE"). When a visitor enters or exits a zone, a structured `Event` is created (e.g., `zone_enter`, `zone_exit`, `queue_join`).
-   **Output**: A time-series log of significant shopper interactions stored in the `events` table.

### 3. Session Reconstruction (`visitor_sessions` table)

-   **Source**: `events` table.
-   **Process**: Events are grouped by `visitor_id` to reconstruct a complete shopper journey, known as a `VisitorSession`. This session aggregates all zone interactions and calculates metrics like total dwell time.
-   **Output**: A `visitor_sessions` table where each row represents one shopper's full journey through the store.

### 4. Commerce Attribution (`brigade_transactions` table)

-   **Source**: `visitor_sessions` and POS data.
-   **Process**: When a visitor enters the `CHECKOUT_QUEUE` zone and a purchase is recorded at the POS around the same time, the system attributes the sale to that `VisitorSession`.
-   **Output**: A link between a CCTV-tracked journey and a real financial transaction.

### 5. Business Insights (`shopper_behavior_service.py`)

-   **Source**: `visitor_sessions`, `brigade_transactions`, and `brand_to_section_mapping.json`.
-   **Process**: The service aggregates data from all sources to calculate high-level business metrics.
    -   It counts visitors and dwell times in each section (from `visitor_sessions`).
    -   It counts purchases in each section (from `brigade_transactions` joined with the brand mapping).
    -   It calculates conversion rates (`purchases / visitors`) for each section.
-   **Output**: Actionable KPIs like **Opportunity Zones** (high traffic, low conversion) and **Checkout Intelligence** (abandonment rate, lost revenue).

This end-to-end flow provides a powerful, data-driven view of how physical store layout and shopper behavior directly impact sales.
