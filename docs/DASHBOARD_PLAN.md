# Retail Analytics Dashboard Design Plan

This document outlines the design plan for a premium, modern Web Dashboard that consumes the current **Retail Intelligence Platform** REST APIs. It establishes layout systems, chart metrics, and overlay mechanics to translate backend telemetry into store intelligence.

---

## 1. Design Aesthetics & Core Theme

* **Color Palette (Modern Dark Mode)**:
  * **Backgrounds**: Slate Gray / Dark Obsidian (`#0F172A`, `#1E293B`) to provide a premium contrast.
  * **Accents / Gradients**: HSL-tailored harmonies:
    * Primary: Electric Indigo (`#6366F1`) to Indigo Violet (`#4F46E5`).
    * Secondary: Emerald Cyan (`#06B6D4` to `#10B981`) for positive conversions.
    * Warnings: Crimson Orange (`#F97316` to `#EF4444`) for anomalies and queue wait warnings.
  * **Card Styling**: Glassmorphic panels with subtle borders (`backdrop-filter: blur(12px)` and `border: 1px solid rgba(255, 255, 255, 0.05)`).
* **Typography**: Clean, geometric sans-serif fonts (e.g. *Outfit* or *Inter* from Google Fonts).

---

## 2. Dashboard Pages & Component Layout

### Page 1: Store Overview (Executive Health)
Provides store managers with high-level operational health indicators and conversion funnels at a glance.
* **Top Metric Cards (KPI Widgets)**:
  1. *Total Visitors*: Displays overall foot traffic (value `visitors` from `/metrics`).
  2. *Engaged Browsing Rate*: Percentage of visitors who enter retail zones (`engaged_visitors` / `visitors`).
  3. *Checkout Queue Traffic*: Count of visitors entering checkout (`billing_queue_visitors`).
  4. *Store Conversion Rate*: Percentage of entries resulting in POS purchases (`conversion_rate` from `/metrics`).
  5. *Avg Store Dwell Time*: Average visit duration in minutes (`avg_session_dwell_ms` formatted to minutes).
* **Primary Visualization (Funnel Chart)**:
  * *Component*: Horizontal 4-Stage Progressive Conversion Funnel (using `/funnel` data).
  * *Design*: Solid block gradients narrowing from Store Entry $\to$ Browsing Aisle $\to$ Queue Join $\to$ Completed Purchase. Includes drop-off rates on hover.
* **Active Alert Panel (Operational Warnings)**:
  * *Component*: Real-time warnings stream (consuming `/anomalies`).
  * *Visuals*: Amber alerts for queue spikes, red alerts for conversion drops, and gray warnings for dead zones.

---

### Page 2: Operations & Queue Performance
Focuses on floor bottlenecks, checkout waiting times, and zone dwell distribution.
* **Metric Cards (Queue Focus)**:
  1. *Average Queue Wait Time*: Dwell duration in billing queue (extracted from `/metrics`).
  2. *Active Checkout Counters*: Simulated counter throughput.
* **Charts**:
  * *Zone Dwell Matrix (Bar Chart)*: Compares visitor count against average dwell times (in seconds) for each zone (Skincare aisle, Billing counter, entryway) using data from `/heatmap/store/{store_id}`.
  * *Hourly Traffic Curve*: Line chart mapping traffic distribution throughout the day.
* **Alert Feed**:
  * *Component*: Log detail showing queue wait spikes (e.g., "Visitor VIS_G022 waited 4.2 minutes at checkout counter").

---

### Page 3: Customer Journeys & Lay-out Audit
Allows floor planners to audit customer journeys and inspect transaction matching parameters.
* **Metric Cards (Cohort Breakdown)**:
  1. *Pass-Throughs (Noise)*: Count of visitors entering and leaving without browsing (`entry_exit_only` from `/journeys`).
  2. *Failed Checkouts (Abandonment)*: Customers who joined the queue but did not link to a purchase (`billing_queue_no_purchase` from `/journeys`).
  3. *Single-Zone Browsers*: Count of narrow-intent shoppers (`single_zone_sessions`).
  4. *Direct Buyers*: Purchases completed with no browsing (`purchase_no_retail_zones`).
* **Interactive Tables**:
  * *Top-10 Longest Journeys Table*: Displays visitor global ID, sequence path (e.g. `[SKINCARE, BILLING]`), total events, and dwell duration (using `longest_journeys` array from `/journeys`).
  * *POS Matching Scores Table*: Displays diagnostic details of transaction-to-session matching scores and confidence metrics (from `/transaction-matches`) to audit register attribution precision.

---

### Page 4: Camera Stitching & Telemetry Diagnostics (Admin Panel)
Allows systems engineers to verify tracking calibration and track stitching accuracy across streams.
* **Diagnostic Widgets**:
  1. *Camera Stitch Ratio*: Average track fragments per visitor (derived from `average_tracks_per_visitor` in `/correlations`).
  2. *Total Track Fragments*: Total raw tracks tracked across all streams.
* **Charts**:
  * *Fragment Distribution Pie*: Compares total tracks detected across camera zones (CAM 1 Entry/Exit vs CAM 2 Skincare vs CAM 4 Checkout).
* **Correlation Grid**:
  * *Component*: Interactive table (consuming `/correlations` data) showing:
    * Global Visitor ID (e.g. `VIS_G017`).
    * Mapped Camera Tracks (e.g. `CAM1_TRACK_65`, `CAM2_TRACK_1`, `CAM2_TRACK_2`).
    * Confidence Rating (HIGH/MEDIUM/LOW badge).

---

## 3. Spatial Heatmap Visualization Approach

To visualize shop floor "hotspots" without heavy video streams, the frontend will overlay zone polygons onto static camera snapshots.

```text
+-----------------------------------------------------------------+
|  CAM 2 - Skincare Aisle Snapshot (Static Background Image)     |
|                                                                 |
|   +------------------------------------+                        |
|   |  Skincare Zone Polygon (SVG)       |                        |
|   |  Dwell Time: 3.2m (Avg)            |                        |
|   |  Fill Color: HSL(0, 100%, 50%, 0.4)|                        |
|   |  (Warm Red Overlay)                |                        |
|   +------------------------------------+                        |
|                                                                 |
|                          +-----------------------------------+  |
|                          | Cosmetics Zone Polygon (SVG)      |  |
|                          | Dwell Time: 12s                   |  |
|                          | Fill Color: HSL(220, 100%, 50%, 0)|  |
|                          | (Cool Blue Overlay)               |  |
|                          +-----------------------------------+  |
+-----------------------------------------------------------------+
```

### Overlay Mechanics:
1. **Background Layer**: Static background snaps of the store camera views (Entryway, Skincare, Checkout) loaded from static assets.
2. **SVG Layer**: Coordinates of zones (loaded from `/sample_store_config/zones.json` coordinates mapped to image pixels) are drawn as interactive SVG `<polygon>` paths on top of the image.
3. **Color Gradient Fill**:
   * Uses HSL coloring: `hsl(H, 100%, 50%, opacity)`.
   * **H (Hue)**: Maps from $240^\circ$ (Cool Blue = low dwell/traffic) to $0^\circ$ (Warm Red = hotspot/high dwell/traffic).
   * **Opacity**: Standardized at `0.4` for visibility of the background image.
4. **Interactions**: Clicking a polygon opens a tooltip showing the exact visitor count and average dwell time for that specific zone (fetched from the heatmap API).
