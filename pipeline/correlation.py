from datetime import datetime
from typing import Any, Sequence
from collections import defaultdict


def _get_field(obj: Any, attr: str, default: Any = None) -> Any:
    """Helper to retrieve attributes from either objects or dicts."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def parse_track_id(visitor_id: str) -> int:
    """Parses track_id integer from visitor_id string (e.g. VIS_003 -> 3)."""
    try:
        if visitor_id.startswith("VIS_"):
            val = visitor_id.split("_")[1]
            digits = "".join([c for c in val if c.isdigit()])
            return int(digits) if digits else 0
    except Exception:
        pass
    return 0


def normalize_camera_id(camera_id: str | None) -> str:
    """Maps detailed camera IDs (e.g. CAM_ENTRY_01) to short logical names (CAM1, CAM2, CAM4)."""
    if not camera_id:
        return "CAM1"
    cam_upper = camera_id.upper()
    if "ENTRY" in cam_upper or "CAM1" in cam_upper:
        return "CAM1"
    elif "SKINCARE" in cam_upper or "CAM2" in cam_upper:
        return "CAM2"
    elif "BILLING" in cam_upper or "CAM4" in cam_upper:
        return "CAM4"
    return "CAM1"


class GlobalVisitorRegistry:
    """Registry maintaining mappings from camera-local tracks to global visitor identities."""

    def __init__(self):
        # Maps (camera_id, track_id) -> global_visitor_id
        self.track_to_global: dict[tuple[str, int], str] = {}
        # Maps global_visitor_id -> list of tracks
        self.global_to_tracks: dict[str, list[dict[str, Any]]] = {}
        # Maps global_visitor_id -> overall correlation confidence
        self.global_confidences: dict[str, str] = {}

    def register_track(self, camera_id: str, track_id: int, global_visitor_id: str, confidence: str = "HIGH") -> None:
        """Registers a track under a global visitor ID and tracks confidence."""
        self.track_to_global[(camera_id, track_id)] = global_visitor_id
        if global_visitor_id not in self.global_to_tracks:
            self.global_to_tracks[global_visitor_id] = []

        track_entry = {"camera_id": camera_id, "track_id": track_id}
        if track_entry not in self.global_to_tracks[global_visitor_id]:
            self.global_to_tracks[global_visitor_id].append(track_entry)

        # Confidence ranking: HIGH (3), MEDIUM (2), LOW (1)
        conf_ranks = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        current_conf = self.global_confidences.get(global_visitor_id, "HIGH")
        if conf_ranks[confidence] < conf_ranks[current_conf]:
            self.global_confidences[global_visitor_id] = confidence
        else:
            self.global_confidences[global_visitor_id] = current_conf

    def get_global_visitor(self, camera_id: str, track_id: int) -> str | None:
        """Retrieves mapped global visitor ID for a local track."""
        return self.track_to_global.get((camera_id, track_id))

    def merge_tracks(self, from_global_id: str, to_global_id: str) -> None:
        """Merges all tracks of one global visitor into another global visitor ID."""
        if from_global_id == to_global_id:
            return

        tracks = self.global_to_tracks.pop(from_global_id, [])
        for track in tracks:
            cam_id = track["camera_id"]
            t_id = track["track_id"]
            self.track_to_global[(cam_id, t_id)] = to_global_id

            if to_global_id not in self.global_to_tracks:
                self.global_to_tracks[to_global_id] = []
            if track not in self.global_to_tracks[to_global_id]:
                self.global_to_tracks[to_global_id].append(track)

        from_conf = self.global_confidences.pop(from_global_id, "HIGH")
        to_conf = self.global_confidences.get(to_global_id, "HIGH")
        conf_ranks = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        if conf_ranks[from_conf] < conf_ranks[to_conf]:
            self.global_confidences[to_global_id] = from_conf


class VisitorCorrelationEngine:
    """Heuristic engine correlating local camera tracks into global visitor sessions."""

    @classmethod
    def correlate_events(cls, events: list[dict]) -> tuple[list[dict], GlobalVisitorRegistry]:
        """Correlates a list of events by mapping their visitor_ids to stitched global visitor IDs."""
        if not events:
            return [], GlobalVisitorRegistry()

        # 1. Group events by (camera_id, track_id)
        grouped_events = defaultdict(list)
        for event in events:
            cam_id = normalize_camera_id(_get_field(event, "camera_id"))
            t_id = parse_track_id(_get_field(event, "visitor_id"))
            grouped_events[(cam_id, t_id)].append(event)

        # 2. Extract track lifecycles
        tracks_lifecycle = []
        for (cam, tid), track_evts in grouped_events.items():
            # Sort events of this track chronologically
            track_evts.sort(key=lambda e: _get_field(e, "timestamp"))
            
            first_ts = datetime.fromisoformat(_get_field(track_evts[0], "timestamp").replace("Z", "+00:00"))
            last_ts = datetime.fromisoformat(_get_field(track_evts[-1], "timestamp").replace("Z", "+00:00"))
            
            # Find EXIT event timestamp for CAM1 tracks if present
            exit_ts = None
            for e in track_evts:
                if _get_field(e, "event_type") == "EXIT":
                    exit_ts = datetime.fromisoformat(_get_field(e, "timestamp").replace("Z", "+00:00"))
                    break
            
            if exit_ts is None:
                exit_ts = last_ts

            tracks_lifecycle.append({
                "camera_id": cam,
                "track_id": tid,
                "first_seen": first_ts,
                "last_seen": last_ts,
                "exit_time": exit_ts,
                "events": track_evts
            })

        # Sort tracks by first seen time to process them in forward chronological order
        tracks_lifecycle.sort(key=lambda t: t["first_seen"])

        registry = GlobalVisitorRegistry()

        # 3. Apply transition heuristics
        for track in tracks_lifecycle:
            cam = track["camera_id"]
            tid = track["track_id"]
            first_seen = track["first_seen"]

            matched_global_id = None
            confidence = "HIGH"

            if cam == "CAM2":
                # Match to preceding CAM1 track (ENTRY exit -> skincare enter)
                candidates = []
                for prev in tracks_lifecycle:
                    if prev["camera_id"] == "CAM1" and prev["exit_time"] <= first_seen:
                        dt = (first_seen - prev["exit_time"]).total_seconds()
                        if 0.0 <= dt <= 30.0:
                            prev_global = registry.get_global_visitor("CAM1", prev["track_id"])
                            if prev_global:
                                candidates.append((dt, prev_global))

                if candidates:
                    # Choose closest timestamp match
                    candidates.sort(key=lambda x: x[0])
                    dt, matched_global_id = candidates[0]
                    # Assign confidence based on temporal proximity
                    if dt <= 10.0:
                        confidence = "HIGH"
                    elif dt <= 20.0:
                        confidence = "MEDIUM"
                    else:
                        confidence = "LOW"

            elif cam == "CAM4":
                # Match to preceding CAM2 track (skincare last seen -> billing counter enter)
                candidates = []
                for prev in tracks_lifecycle:
                    if prev["camera_id"] == "CAM2" and prev["last_seen"] <= first_seen:
                        dt = (first_seen - prev["last_seen"]).total_seconds()
                        if 0.0 <= dt <= 60.0:
                            prev_global = registry.get_global_visitor("CAM2", prev["track_id"])
                            if prev_global:
                                candidates.append((dt, prev_global))

                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    dt, matched_global_id = candidates[0]
                    if dt <= 15.0:
                        confidence = "HIGH"
                    elif dt <= 30.0:
                        confidence = "MEDIUM"
                    else:
                        confidence = "LOW"
                else:
                    # Fallback straight transition: CAM1 -> CAM4 (entry -> checkout directly)
                    candidates_entry = []
                    for prev in tracks_lifecycle:
                        if prev["camera_id"] == "CAM1" and prev["exit_time"] <= first_seen:
                            dt = (first_seen - prev["exit_time"]).total_seconds()
                            if 0.0 <= dt <= 90.0:
                                prev_global = registry.get_global_visitor("CAM1", prev["track_id"])
                                if prev_global:
                                    candidates_entry.append((dt, prev_global))

                    if candidates_entry:
                        candidates_entry.sort(key=lambda x: x[0])
                        dt, matched_global_id = candidates_entry[0]
                        if dt <= 20.0:
                            confidence = "HIGH"
                        elif dt <= 45.0:
                            confidence = "MEDIUM"
                        else:
                            confidence = "LOW"

            if matched_global_id:
                registry.register_track(cam, tid, matched_global_id, confidence)
            else:
                # Assign new global visitor ID
                new_global_id = f"VIS_G{len(registry.global_to_tracks) + 1:03d}"
                registry.register_track(cam, tid, new_global_id, "HIGH")

        # 4. Map events to the global visitor IDs and add diagnostics metadata
        correlated_events = []
        for event in events:
            cam_detailed = _get_field(event, "camera_id")
            cam_norm = normalize_camera_id(cam_detailed)
            tid = parse_track_id(_get_field(event, "visitor_id"))

            global_visitor_id = registry.get_global_visitor(cam_norm, tid) or _get_field(event, "visitor_id")
            
            # Create a copy and update attributes
            evt_copy = dict(event)
            evt_copy["visitor_id"] = global_visitor_id
            
            # Embed diagnostics metadata for retrieval in diagnostics endpoint
            evt_copy["metadata"] = {
                "original_track_id": tid,
                "original_camera_id": cam_detailed,
                "correlation_confidence": registry.global_confidences.get(global_visitor_id, "HIGH")
            }
            correlated_events.append(evt_copy)

        return correlated_events, registry
