# CV Pipeline Assumptions & Tradeoffs - Sprint 14

This document outlines the explicitly chosen architectural constraints, shortcuts, and tradeoffs applied during the Sprint 14 Detection MVP implementation.

## 1. Visitor Tracking Mapping
* **Assumption**: `visitor_id == track_id`
* **Shortcut**: The persistent ID assigned by YOLOv8/ByteTrack (`1`, `2`, `3`, etc.) is directly mapped to the visitor ID schema prefix (`VIS_001`, `VIS_002`, etc.).
* **Tradeoff**: In a real multi-camera environment, re-identification (Re-ID) must run across camera streams to link the same visitor across camera views. We bypass cross-camera Re-ID in the MVP by treating the camera tracking ID as a unique global customer identifier.

## 2. Spatial Exit Detection
* **Assumption**: Track disappearance represents store exit.
* **Shortcut**: An `EXIT` event is triggered when a tracked visitor disappears from the camera frame for `EXIT_TIMEOUT_FRAMES` (default 30 frames).
* **Tradeoff**: Rather than forcing visitors to exit through the entrance/exit polygon (which frequently fails due to camera limits, occlusion, or path variations), we rely on disappearance timeouts. This avoids false negatives where visitors leave without triggering a spatial line-crossing event.

## 3. Debouncing Zone Changes
* **Assumption**: Smooth transitions on retail zone boundaries.
* **Shortcut**: A track must stay in a candidate zone for `ZONE_CHANGE_DEBOUNCE_FRAMES` (default 10 frames) before a transition is officially registered.
* **Tradeoff**: Bounding box jitter around polygon edges is smoothed out, preventing rapid oscillations of `ZONE_ENTER` and `ZONE_EXIT` events.

## 4. Dwell Time Aggregation
* **Assumption**: `ZONE_DWELL` events are aggregated.
* **Shortcut**: Dwell events are not emitted on every frame. Instead, a `ZONE_DWELL` is emitted with total accumulated duration in milliseconds only when a track exits a zone or periodically every `MIN_DWELL_SECONDS` (default 5 seconds).
* **Tradeoff**: Prevents database event bloating (a person staying in a zone at 30 FPS would generate 1800 events/minute).

## 5. Staff and Re-entry Detection
* **Assumption**: Uniform-based staff classification is not implemented.
* **Shortcut**: Schema and API layers fully support staff exclusion. All edge events generated currently default to `is_staff = false`.
* **Tradeoff**: Honest and technically defensible architecture design; backend correctly ignores and filters out staff sessions when ingested with `is_staff = true` from external validation runs, without relying on speculative uniform classifiers.
