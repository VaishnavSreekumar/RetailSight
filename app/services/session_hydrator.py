import uuid
from collections import defaultdict
from typing import Any, Sequence

from app.models.visitor_session import VisitorSession


def _get_field(obj: Any, attr: str, default: Any = None) -> Any:
    """Helper to retrieve attributes from either objects or dicts."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


class SessionHydrator:
    """Service class responsible for transforming Event sequences into VisitorSession state."""

    @staticmethod
    def hydrate_sessions(events: Sequence[Any]) -> list[VisitorSession]:
        """Consumes ordered Event records and aggregates them into VisitorSession models.

        Groups events by visitor and store, sorts them chronologically, and executes
        the session state transition state-machine.
        """
        if not events:
            return []

        # 1. Group events by (visitor_id, store_id)
        grouped_events = defaultdict(list)
        for event in events:
            visitor_id = _get_field(event, "visitor_id")
            store_id = _get_field(event, "store_id")
            if visitor_id and store_id:
                grouped_events[(visitor_id, store_id)].append(event)

        completed_sessions: list[VisitorSession] = []

        # 2. Process each group's event sequence chronologically
        for (visitor_id, store_id), visitor_events in grouped_events.items():
            # Sort events by timestamp
            sorted_events = sorted(
                visitor_events, key=lambda e: _get_field(e, "timestamp")
            )

            current_session: VisitorSession | None = None

            for event in sorted_events:
                event_type = _get_field(event, "event_type")
                timestamp = _get_field(event, "timestamp")
                is_staff = _get_field(event, "is_staff", False)
                zone_id = _get_field(event, "zone_id")
                dwell_ms = _get_field(event, "dwell_ms")

                # If no session is currently active
                if current_session is None:
                    # Initialize a new session
                    current_session = VisitorSession(
                        id=uuid.uuid4(),
                        visitor_id=visitor_id,
                        store_id=store_id,
                        entered_at=timestamp,
                        exited_at=None,
                        journey_path=[],
                        zone_dwell_times={},
                        zone_transitions={},
                        is_staff=is_staff,
                        has_converted=False,
                        has_joined_billing_queue=False,
                        associated_txn_id=None,
                        intent_score=0.0,
                    )

                # Process event metrics under the active session
                if event_type in ("ENTRY", "REENTRY"):
                    # If this entry is occurring on an already active session, ignore/no-op
                    # If we started it just above, entered_at is already set correctly.
                    pass

                elif event_type == "ZONE_ENTER":
                    if zone_id:
                        path = current_session.journey_path or []
                        # Avoid adding consecutive duplicate zones
                        if not path or path[-1] != zone_id:
                            path.append(zone_id)
                        current_session.journey_path = path

                elif event_type in ("ZONE_DWELL", "ZONE_EXIT"):
                    if zone_id and dwell_ms is not None:
                        dwells = current_session.zone_dwell_times or {}
                        dwells[zone_id] = dwells.get(zone_id, 0) + dwell_ms
                        current_session.zone_dwell_times = dwells

                elif event_type == "BILLING_QUEUE_JOIN":
                    current_session.has_joined_billing_queue = True

                elif event_type == "EXIT":
                    current_session.exited_at = timestamp
                    completed_sessions.append(current_session)
                    current_session = None

            # If the event sequence ended but a session is still active (no EXIT event seen)
            if current_session is not None:
                completed_sessions.append(current_session)

        return completed_sessions
