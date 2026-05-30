from collections import defaultdict
from typing import Any, Sequence
from pipeline.correlation import normalize_camera_id


class CorrelationDiagnosticsService:
    """Service designed to evaluate and compile diagnostic reports on track-stitching correlations."""

    @staticmethod
    def get_correlations(events: Sequence[Any]) -> dict[str, Any]:
        """Analyzes event records and reconstructs the mapped track-stitching correlation lists and summary stats."""
        # Maps global_visitor_id -> set of track tuples (normalized_camera_id, track_id)
        visitor_tracks = defaultdict(set)
        # Maps global_visitor_id -> set of confidence strings
        visitor_confidences = defaultdict(set)

        for event in events:
            visitor_id = getattr(event, "visitor_id", None)
            camera_id = getattr(event, "camera_id", None)
            metadata = getattr(event, "event_metadata", None) or {}

            # Handle case if they are dictionaries
            if isinstance(event, dict):
                visitor_id = event.get("visitor_id")
                camera_id = event.get("camera_id")
                metadata = event.get("metadata") or {}

            if not visitor_id or not camera_id:
                continue

            track_id = metadata.get("original_track_id")
            confidence = metadata.get("correlation_confidence", "HIGH")

            if track_id is not None:
                norm_cam = normalize_camera_id(camera_id)
                visitor_tracks[str(visitor_id)].add((norm_cam, int(track_id)))
                visitor_confidences[str(visitor_id)].add(str(confidence))

        correlations_list = []
        total_track_fragments = 0

        for visitor_id, tracks_set in visitor_tracks.items():
            # Convert set of tuples to list of dicts
            tracks = []
            for cam, tid in sorted(list(tracks_set), key=lambda x: (x[0], x[1])):
                tracks.append({"camera_id": cam, "track_id": tid})

            total_track_fragments += len(tracks)

            # Determine the consensus confidence (choose the worst/lowest one present: HIGH > MEDIUM > LOW)
            conf_ranks = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            sorted_confs = sorted(list(visitor_confidences[visitor_id]), key=lambda c: conf_ranks.get(c, 3))
            worst_conf = sorted_confs[0] if sorted_confs else "HIGH"

            correlations_list.append({
                "global_visitor_id": visitor_id,
                "tracks": tracks,
                "confidence": worst_conf,
            })

        # Sort correlations by global_visitor_id
        correlations_list.sort(key=lambda c: c["global_visitor_id"])

        total_global_visitors = len(correlations_list)
        avg_tracks_per_visitor = 0.0
        if total_global_visitors > 0:
            avg_tracks_per_visitor = round(total_track_fragments / total_global_visitors, 2)

        return {
            "correlations": correlations_list,
            "summary": {
                "total_global_visitors": total_global_visitors,
                "total_track_fragments": total_track_fragments,
                "average_tracks_per_visitor": avg_tracks_per_visitor,
            }
        }
