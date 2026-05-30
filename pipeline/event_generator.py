from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from pipeline.models import GeneratedEvent, Track
from pipeline.zones import ZoneEngine


class TrackState:
    """State model tracking the lifecycle and spatial status of a visitor track."""

    def __init__(self, track_id: int, start_frame: int, store_id: str):
        self.track_id = track_id
        self.visitor_id = f"VIS_{track_id:03d}"
        self.store_id = store_id
        self.last_seen_frame = start_frame
        self.confidences: list[float] = []

        # State flags
        self.has_entered_store = False
        self.has_joined_billing = False

        # Retail zone tracking
        self.current_zone: str | None = None
        self.zone_dwell_start_frame: int | None = None
        self.last_dwell_emission_frame: int | None = None

        # Debounce tracking
        self.candidate_zone: str | None = None
        self.consecutive_frames_in_zone = 0

    def get_average_confidence(self) -> float:
        """Returns average detection confidence recorded for this track."""
        if not self.confidences:
            return 1.0
        return sum(self.confidences) / len(self.confidences)


class EventGenerator:
    """State machine converting tracked person paths into debounced retail events."""

    def __init__(
        self,
        zone_engine: ZoneEngine,
        store_id: str,
        fps: float = 30.0,
        start_time: datetime | None = None,
        exit_timeout_frames: int = 30,
        zone_debounce_frames: int = 10,
        min_dwell_seconds: float = 5.0,
        camera_id: str | None = None,
    ):
        self.zone_engine = zone_engine
        self.store_id = store_id
        self.fps = fps
        self.start_time = start_time or datetime.now(timezone.utc)
        self.exit_timeout_frames = exit_timeout_frames
        self.zone_debounce_frames = zone_debounce_frames
        self.min_dwell_seconds = min_dwell_seconds
        self.camera_id = camera_id

        # Map of track_id -> TrackState
        self.active_tracks: dict[int, TrackState] = {}

    def get_timestamp_for_frame(self, frame_idx: int) -> str:
        """Calculates ISO-8601 formatted timestamp for a given frame index."""
        delta = timedelta(seconds=frame_idx / self.fps)
        return (self.start_time + delta).isoformat()

    def process_frame(
        self, frame_idx: int, tracks: Sequence[Track]
    ) -> list[GeneratedEvent]:
        """Processes frame-by-frame visitor tracks and yields triggered retail events."""
        events: list[GeneratedEvent] = []
        timestamp = self.get_timestamp_for_frame(frame_idx)
        seen_track_ids = set()

        for track in tracks:
            track_id = track.track_id
            seen_track_ids.add(track_id)

            # Initialize track state if seen for the first time
            if track_id not in self.active_tracks:
                self.active_tracks[track_id] = TrackState(
                    track_id, frame_idx, self.store_id
                )

            state = self.active_tracks[track_id]
            state.last_seen_frame = frame_idx
            state.confidences.append(track.confidence)
            avg_conf = state.get_average_confidence()

            # 1. ENTRY Detection
            if not state.has_entered_store:
                if self.zone_engine.is_in_entry(track):
                    state.has_entered_store = True
                    events.append(
                        GeneratedEvent(
                            event_type="ENTRY",
                            visitor_id=state.visitor_id,
                            store_id=self.store_id,
                            timestamp=timestamp,
                            confidence=avg_conf,
                        )
                    )

            # 2. Zone Change & Transition Debouncing
            active_retail_zone = self.zone_engine.get_retail_zone(track)

            if active_retail_zone != state.current_zone:
                if active_retail_zone == state.candidate_zone:
                    state.consecutive_frames_in_zone += 1
                else:
                    state.candidate_zone = active_retail_zone
                    state.consecutive_frames_in_zone = 1

                # If the track has stayed in the candidate zone long enough, commit change
                if state.consecutive_frames_in_zone >= self.zone_debounce_frames:
                    # Exit the previous zone if one was active
                    if state.current_zone is not None:
                        dwell_frames = frame_idx - state.zone_dwell_start_frame
                        dwell_ms = int((dwell_frames / self.fps) * 1000)
                        events.append(
                            GeneratedEvent(
                                event_type="ZONE_EXIT",
                                visitor_id=state.visitor_id,
                                store_id=self.store_id,
                                timestamp=timestamp,
                                confidence=avg_conf,
                                zone_id=state.current_zone,
                            )
                        )
                        events.append(
                            GeneratedEvent(
                                event_type="ZONE_DWELL",
                                visitor_id=state.visitor_id,
                                store_id=self.store_id,
                                timestamp=timestamp,
                                confidence=avg_conf,
                                zone_id=state.current_zone,
                                dwell_ms=dwell_ms,
                            )
                        )

                    # Enter the new zone
                    state.current_zone = active_retail_zone
                    state.consecutive_frames_in_zone = 0
                    state.candidate_zone = None

                    if state.current_zone is not None:
                        state.zone_dwell_start_frame = frame_idx
                        state.last_dwell_emission_frame = frame_idx
                        events.append(
                            GeneratedEvent(
                                event_type="ZONE_ENTER",
                                visitor_id=state.visitor_id,
                                store_id=self.store_id,
                                timestamp=timestamp,
                                confidence=avg_conf,
                                zone_id=state.current_zone,
                            )
                        )
            else:
                # Reset candidate trackers if track remains in the current zone
                state.candidate_zone = None
                state.consecutive_frames_in_zone = 0

            # 3. Periodic ZONE_DWELL Emission (avoiding event bloating)
            if state.current_zone is not None and state.last_dwell_emission_frame is not None:
                elapsed_frames = frame_idx - state.last_dwell_emission_frame
                elapsed_seconds = elapsed_frames / self.fps
                if elapsed_seconds >= self.min_dwell_seconds:
                    dwell_ms = int(elapsed_seconds * 1000)
                    events.append(
                        GeneratedEvent(
                            event_type="ZONE_DWELL",
                            visitor_id=state.visitor_id,
                            store_id=self.store_id,
                            timestamp=timestamp,
                            confidence=avg_conf,
                            zone_id=state.current_zone,
                            dwell_ms=dwell_ms,
                        )
                    )
                    state.last_dwell_emission_frame = frame_idx

            # 4. BILLING_QUEUE_JOIN Detection
            if not state.has_joined_billing:
                if self.zone_engine.is_in_billing(track):
                    state.has_joined_billing = True
                    events.append(
                        GeneratedEvent(
                            event_type="BILLING_QUEUE_JOIN",
                            visitor_id=state.visitor_id,
                            store_id=self.store_id,
                            timestamp=timestamp,
                            confidence=avg_conf,
                        )
                    )

        # 5. Track Disappearance & EXIT Detection
        disappeared_track_ids = []
        for track_id, state in self.active_tracks.items():
            if track_id not in seen_track_ids:
                if frame_idx - state.last_seen_frame >= self.exit_timeout_frames:
                    disappeared_track_ids.append(track_id)
                    avg_conf = state.get_average_confidence()

                    # Exit retail zone if still inside one
                    if state.current_zone is not None and state.zone_dwell_start_frame is not None:
                        # Dwell counts up to the last frame the track was visible
                        dwell_frames = state.last_seen_frame - state.zone_dwell_start_frame
                        dwell_ms = max(0, int((dwell_frames / self.fps) * 1000))
                        last_seen_timestamp = self.get_timestamp_for_frame(state.last_seen_frame)
                        events.append(
                            GeneratedEvent(
                                event_type="ZONE_EXIT",
                                visitor_id=state.visitor_id,
                                store_id=self.store_id,
                                timestamp=last_seen_timestamp,
                                confidence=avg_conf,
                                zone_id=state.current_zone,
                            )
                        )
                        events.append(
                            GeneratedEvent(
                                event_type="ZONE_DWELL",
                                visitor_id=state.visitor_id,
                                store_id=self.store_id,
                                timestamp=last_seen_timestamp,
                                confidence=avg_conf,
                                zone_id=state.current_zone,
                                dwell_ms=dwell_ms,
                            )
                        )

                    # Generate final EXIT event at the last visible frame
                    if state.has_entered_store:
                        last_seen_timestamp = self.get_timestamp_for_frame(state.last_seen_frame)
                        events.append(
                            GeneratedEvent(
                                event_type="EXIT",
                                visitor_id=state.visitor_id,
                                store_id=self.store_id,
                                timestamp=last_seen_timestamp,
                                confidence=avg_conf,
                            )
                        )

        # Clean up memory by removing inactive tracks
        for track_id in disappeared_track_ids:
            del self.active_tracks[track_id]

        for e in events:
            e.camera_id = self.camera_id

        return events
