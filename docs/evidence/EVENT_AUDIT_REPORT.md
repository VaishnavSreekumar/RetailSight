# EVENT_AUDIT_REPORT.md

This document presents the event quality audit metrics comparing the Retail Intelligence Platform database before and after implementing the Sprint 25 duplicate prevention and data quality enhancements.

---

## 1. Quality Metrics Audit

Below is a summary of database metrics showing event quality, duplicate detection, and session hydration accuracy before and after Sprint 25.

### Before Sprint 25

* **Events**: 544
* **Duplicate ENTRYs**: 57
* **Duplicate ZONE_ENTERs**: 125
* **Sessions**: 64

### After Sprint 25

* **Events**: 355
* **Duplicate ENTRYs**: 0
* **Duplicate ZONE_ENTERs**: 0
* **Sessions**: 74

---

## 2. Real Database Example: `VIS_001` Journey

Here is the exact sequential event log and hydrated session for visitor `VIS_001` retrieved from the PostgreSQL database after running the Sprint 25 pipeline.

### Raw Event Log (Ordered Chronologically)

| visitor_id | event_type | timestamp | zone_id | dwell_ms | camera_id |
|---|---|---|---|---|---|
| **VIS_001** | `ENTRY` | `2026-05-31T12:00:34.285049+00:00` | *None* | *None* | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_ENTER` | `2026-05-31T12:00:34.585349+00:00` | `SKINCARE` | *None* | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:00:39.590349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:00:44.595349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:00:49.600349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:00:54.605349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:00:59.610349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:01:04.615349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:01:09.620349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:01:14.625349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:01:19.630349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:01:24.635349+00:00` | `SKINCARE` | `5005` | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_EXIT` | `2026-05-31T12:01:25.536249+00:00` | `SKINCARE` | *None* | `CAM_ENTRY_01` |
| **VIS_001** | `ZONE_DWELL` | `2026-05-31T12:01:25.536249+00:00` | `SKINCARE` | `900` | `CAM_ENTRY_01` |
| **VIS_001** | `EXIT` | `2026-05-31T12:01:25.536249+00:00` | *None* | *None* | `CAM_ENTRY_01` |

### Resulting `visitor_session` Database Row

* **session_id**: `d1421f15-bf27-4632-9cb8-b2ef56a5b28d` (UUID generated on hydration)
* **visitor_id**: `VIS_001`
* **store_id**: `STORE_VAL_01`
* **entered_at**: `2026-05-31T12:00:34.285049+00:00`
* **exited_at**: `2026-05-31T12:01:25.536249+00:00`
* **journey_path**: `["SKINCARE"]` (consecutive duplicates automatically collapsed/ignored)
* **zone_dwell_times**: `{"SKINCARE": 50950}` (sum of `5005 * 10 + 900` incremental dwell times)
* **is_staff**: `false`
* **has_converted**: `false`
* **has_joined_billing_queue**: `false`

---

## 3. Key Achievements & Verification Details

1. **Deterministic Idempotency**:
   Running the validation pipeline consecutively twice produces exactly **355 events** in the database. The second run records **0 new event insertions** and **355 duplicate warnings** on conflict, keeping the total visitor sessions at exactly **74**.
2. **Generation-Level Prevention**:
   The `EventGenerator` active-track check prevents duplicate emissions of `ENTRY` and `ZONE_ENTER` events at frame time, eliminating the root cause of event bloating.
3. **Safety-Net Hydration Filtering**:
   `SessionHydrator` rejects exact duplicates and ignores consecutive duplicate events, ensuring only valid transitions impact customer journey paths.
