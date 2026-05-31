# Deliverable Verification Report

This report verifies the technical completeness of the 7 core delivery stages of the **Retail Intelligence Platform**, detailing files involved, verification evidence (from our E2E run), and unit test coverage.

---

## 1. Raw CCTV → Events
Converts streaming CCTV raw footage coordinates to discrete store events (`ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL`, `BILLING_QUEUE_JOIN`).

* **Files Involved**:
  * [pipeline/runner.py](file:///c:/Users/vaish/retail-intelligence/pipeline/runner.py): Controls frame-by-frame loading.
  * [pipeline/tracker.py](file:///c:/Users/vaish/retail-intelligence/pipeline/tracker.py): Handles YOLOv8 person detection and ByteTrack tracking.
  * [pipeline/zones.py](file:///c:/Users/vaish/retail-intelligence/pipeline/zones.py): Spatial polygon checks using Shapely.
  * [pipeline/event_generator.py](file:///c:/Users/vaish/retail-intelligence/pipeline/event_generator.py): Debounces transitions and manages exit timeouts.
  * [pipeline/config.py](file:///c:/Users/vaish/retail-intelligence/pipeline/config.py): Contains parameters (`EXIT_TIMEOUT_FRAMES = 30`, `ZONE_CHANGE_DEBOUNCE_FRAMES = 10`, `MIN_DWELL_SECONDS = 5.0`).
* **Verification Evidence**:
  * Output files saved: `pipeline/output/e2e_cam1.jsonl` (29 events), `e2e_cam2.jsonl` (99 events), `e2e_cam4.jsonl` (2 events).
  * Sample event logs during extraction:
    * `[Frame 0] Emitted event: ENTRY | Visitor: VIS_001 | Zone: None`
    * `[Frame 98] Emitted event: ZONE_EXIT | Visitor: VIS_002 | Zone: SKINCARE`
    * `[Frame 652] Emitted event: BILLING_QUEUE_JOIN | Visitor: VIS_002 | Zone: None`
* **Test Coverage**:
  * `tests/test_detection_pipeline.py`: Verifies bounding box mappings and Shapely intersection logic.
  * `tests/test_events.py`: Verifies `GeneratedEvent` parsing and JSON schema constraints.

---

## 2. Events → Sessions (Hydration)
Aggregates unstructured, time-series raw events into structured, persistent visitor sessions containing entrance time, exit time, zone paths, and dwell durations.

* **Files Involved**:
  * [app/services/session_hydration_service.py](file:///c:/Users/vaish/retail-intelligence/app/services/session_hydration_service.py): Reconstructs visitor timelines.
  * [app/models/event.py](file:///c:/Users/vaish/retail-intelligence/app/models/event.py): The database model for `Event`.
  * [app/models/visitor_session.py](file:///c:/Users/vaish/retail-intelligence/app/models/visitor_session.py): The database model for `VisitorSession`.
  * [app/api/v1/endpoints/stores.py](file:///c:/Users/vaish/retail-intelligence/app/api/v1/endpoints/stores.py): Implements `POST /stores/{store_id}/hydrate`.
* **Verification Evidence**:
  * Event Ingestion API Response: `{'ingested_count': 130, 'duplicate_count': 0, 'failed_count': 0, 'errors': []}`.
  * Hydration Trigger API Response: `{'hydrated_count': 60, 'linked_count': 1}`.
  * DB records verify the creation of 60 hydrated sessions mapped to store `STORE_E2E_01`.
* **Test Coverage**:
  * `tests/test_session_hydration_service.py`: Mocks database events and verifies output session details (start, end, path).
  * `tests/test_session_hydrator.py`: Evaluates state transitions of the hydrator state-machine.

---

## 3. Sessions → Metrics
Calculates consolidated high-level performance indicators for a store location, such as traffic volume, visitor engagement, checkout counts, and conversion rate.

* **Files Involved**:
  * [app/services/metrics_service.py](file:///c:/Users/vaish/retail-intelligence/app/services/metrics_service.py): Consolidates metrics.
  * [app/api/v1/endpoints/stores.py](file:///c:/Users/vaish/retail-intelligence/app/api/v1/endpoints/stores.py): Implements `GET /stores/{store_id}/metrics`.
  * [app/schemas/metrics.py](file:///c:/Users/vaish/retail-intelligence/app/schemas/metrics.py): Pydantic validation for `StoreMetrics`.
* **Verification Evidence**:
  * Fetching `GET /api/v1/stores/STORE_E2E_01/metrics` returns:
    ```json
    {
      "store_id": "STORE_E2E_01",
      "visitors": 60,
      "engaged_visitors": 10,
      "billing_queue_visitors": 4,
      "purchases": 1,
      "conversion_rate": 1.67,
      "avg_session_dwell_ms": 121894.41,
      "avg_journey_length": 0.17,
      "avg_zones_visited": 0.17
    }
    ```
* **Test Coverage**:
  * `tests/test_metrics_service.py`: Verifies average dwell computation, conversion calculations, and metric limits.
  * `tests/test_metrics_endpoint.py`: Validates schema output structure and error handlers.

---

## 4. Sessions → Funnel
Maps structured sessions to a progressive conversion cohort representing the classic customer retail progression: Entry $\to$ Browsing $\to$ Queue $\to$ Purchase.

* **Files Involved**:
  * [app/services/funnel_service.py](file:///c:/Users/vaish/retail-intelligence/app/services/funnel_service.py): Generates conversion rates per stage.
  * [app/api/v1/endpoints/stores.py](file:///c:/Users/vaish/retail-intelligence/app/api/v1/endpoints/stores.py): Implements `GET /stores/{store_id}/funnel`.
  * [app/schemas/funnel.py](file:///c:/Users/vaish/retail-intelligence/app/schemas/funnel.py): Pydantic validation for `FunnelReport`.
* **Verification Evidence**:
  * Fetching `GET /api/v1/stores/STORE_E2E_01/funnel` returns:
    ```json
    {
      "store_id": "STORE_E2E_01",
      "steps": [
        { "step_name": "Store Entry", "visitor_count": 60, "conversion_rate": 100.0 },
        { "step_name": "Browsing Zones", "visitor_count": 10, "conversion_rate": 16.67 },
        { "step_name": "Checkout Counter", "visitor_count": 4, "conversion_rate": 40.0 },
        { "step_name": "Completed Purchase", "visitor_count": 1, "conversion_rate": 25.0 }
      ]
    }
    ```
* **Test Coverage**:
  * `tests/test_funnel_service.py`: Confirms ratios calculations and edge cases (e.g. 0 entries).
  * `tests/test_funnel_endpoint.py`: Tests API route mapping.

---

## 5. Sessions → Anomalies
Scans hydrated session data to detect shop floor operational issues like checkout bottlenecks, conversion drops, and dead zones.

* **Files Involved**:
  * [app/services/anomaly_service.py](file:///c:/Users/vaish/retail-intelligence/app/services/anomaly_service.py): Identifies queue spikes, conversion dips, and zone inactivity.
  * [app/api/v1/endpoints/stores.py](file:///c:/Users/vaish/retail-intelligence/app/api/v1/endpoints/stores.py): Implements `GET /stores/{store_id}/anomalies`.
* **Verification Evidence**:
  * `GET /api/v1/stores/STORE_E2E_01/anomalies` returns `[]` (representing no current threshold breaches on this small slice of video data).
* **Test Coverage**:
  * `tests/test_anomaly_engine.py`: Verifies queue wait threshold limits, conversion dips below historical baseline, and dead zone triggers.
  * `tests/test_anomaly_endpoint.py`: Confirms REST schema compliance.

---

## 6. Sessions → Transactions
Correlates visitor checkouts with cash-register POS receipts based on temporal proximity and queue presence.

* **Files Involved**:
  * [app/services/transaction_matcher.py](file:///c:/Users/vaish/retail-intelligence/app/services/transaction_matcher.py): Implements match scoring algorithm.
  * [app/models/transaction.py](file:///c:/Users/vaish/retail-intelligence/app/models/transaction.py): Database model for `Transaction`.
  * [app/api/v1/endpoints/stores.py](file:///c:/Users/vaish/retail-intelligence/app/api/v1/endpoints/stores.py): Implements `GET /stores/{store_id}/transaction-matches`.
* **Verification Evidence**:
  * Log indicates: `Inserted mock POS transaction TXN_E2E_001 in DB.`
  * Fetching transaction matching diagnostics returns:
    ```json
    {
      "matched": [
        {
          "session_id": "969ee338-b2af-446c-a289-502efb5dbf0e",
          "transaction_id": "TXN_E2E_001",
          "match_score": 26.14,
          "match_confidence": "LOW"
        }
      ]
    }
    ```
* **Test Coverage**:
  * `tests/test_transaction_matcher.py`: Validates multiplier score impacts from queue checkouts and window boundaries.

---

## 7. Cross-Camera Correlation
Resolves multi-camera track fragmentation by stitching camera-local track IDs into unified global visitor identities.

* **Files Involved**:
  * [pipeline/correlation.py](file:///c:/Users/vaish/retail-intelligence/pipeline/correlation.py): The main stitching state machine.
  * [app/services/correlation_diagnostics.py](file:///c:/Users/vaish/retail-intelligence/app/services/correlation_diagnostics.py): Reconstructs mappings from raw JSONB event logs.
  * [app/api/v1/endpoints/stores.py](file:///c:/Users/vaish/retail-intelligence/app/api/v1/endpoints/stores.py): Implements `GET /stores/{store_id}/correlations`.
* **Verification Evidence**:
  * Logs from E2E runner:
    ```text
    --- Correlation Engine Metrics ---
    Total Global Visitors Registered: 22
    Total Local Tracks Mapped: 44
      VIS_G001 (Confidence: HIGH) -> CAM1_TRACK_1
      ...
      VIS_G017 (Confidence: LOW) -> CAM1_TRACK_65, CAM2_TRACK_1, CAM2_TRACK_2, CAM2_TRACK_3, CAM2_TRACK_4...
      VIS_G022 (Confidence: LOW) -> CAM2_TRACK_134, CAM4_TRACK_2, CAM4_TRACK_3
    ```
  * Reconstructs 22 global visitor paths with an average of 2.0 camera track fragments stitched per visitor.
* **Test Coverage**:
  * `tests/test_correlation.py`: Tests track parsing, camera name normalization, transition rules (Rules 1-4), topological constraints, and `/correlations` REST route.

---

## 8. Business Insights & Retail Commerce
Leverages the **real Brigade Road, Bangalore transaction dataset** to generate strongly typed retail analytics and correlate physical in-store paths with cashier purchases.

* **Files Involved**:
  * [app/analytics/data_profiler.py](file:///c:/Users/vaish/retail-intelligence/app/analytics/data_profiler.py): Automates dataset profiling.
  * [app/services/retail_insights_service.py](file:///c:/Users/vaish/retail-intelligence/app/services/retail_insights_service.py): Calculates standard retail revenue, product, offer, and employee KPIs.
  * [app/services/journey_commerce_service.py](file:///c:/Users/vaish/retail-intelligence/app/services/journey_commerce_service.py): Stitches physical zone dwells with transaction shopping baskets.
  * [app/schemas/insights.py](file:///c:/Users/vaish/retail-intelligence/app/schemas/insights.py): Strongly typed validation models for insights responses.
  * [app/api/v1/endpoints/stores.py](file:///c:/Users/vaish/retail-intelligence/app/api/v1/endpoints/stores.py): Exposes 5 REST routes under `/stores/{store_id}/insights/*` and `/executive-summary`.
* **Verification Evidence**:
  * Profiling verified **101 transaction rows**, ₹34,831.74 total Net Merchandise Value, and ₹1,451.32 Average Basket Value.
  * `GET /api/v1/stores/ST1008/executive-summary` returns:
    ```json
    {
      "revenue": 34831.74,
      "top_category": "makeup",
      "top_brand": "Faces Canada",
      "best_offer": "Buy 2 Get 1 Faces and Ny bae",
      "top_salesperson": "Zufishan Khazra",
      "conversion_rate": 38.46,
      "highest_performing_zone": "ZONE_COSMETICS",
      "opportunity_zone": "ZONE_SKINCARE"
    }
    ```
* **Test Coverage**:
  * `tests/test_retail_insights_service.py`: Validates revenue totals, product category lists, applied campaign rates, and salesperson totals.
  * `tests/test_journey_commerce_service.py`: Audits dwell-to-purchase percentages, checkout abandonment values, and opportunity loss severity.
  * `tests/test_executive_summary_endpoint.py`: Validates all five REST routes under client mock routing.
  * **Test Suite passes 59/59 successfully!**

