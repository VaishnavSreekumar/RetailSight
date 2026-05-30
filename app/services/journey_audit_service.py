from collections import defaultdict
from typing import Any, Sequence
from datetime import datetime

from app.models.visitor_session import VisitorSession
from app.models.transaction import Transaction


def _get_field(obj: Any, attr: str, default: Any = None) -> Any:
    """Helper to retrieve attributes from either objects or dicts."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


class JourneyAuditService:
    """Service class designed to analyze customer journeys and perform diagnostic checks."""

    @classmethod
    def audit_cohort(
        cls,
        sessions: Sequence[Any],
        transactions: Sequence[Any],
        events: Sequence[Any],
    ) -> dict[str, Any]:
        """Maps visitor sessions into formatted journey structures and filters them into diagnostic categories."""
        # 1. Group events by visitor_id for quick time window queries
        events_by_visitor = defaultdict(list)
        for event in events:
            v_id = _get_field(event, "visitor_id")
            if v_id:
                events_by_visitor[str(v_id)].append(event)

        # 2. Build a map of transactions for easy lookup by associated_txn_id
        txn_map = {}
        for txn in transactions:
            t_id = _get_field(txn, "id")
            if t_id:
                txn_map[str(t_id)] = txn

        # 3. Construct JourneySchema objects for all sessions
        journey_list = []
        for session in sessions:
            s_id = _get_field(session, "id")
            visitor_id = _get_field(session, "visitor_id")
            journey_path = _get_field(session, "journey_path", []) or []
            entered_at = _get_field(session, "entered_at")
            exited_at = _get_field(session, "exited_at")
            joined_billing_queue = bool(_get_field(session, "has_joined_billing_queue", False))
            associated_txn_id = _get_field(session, "associated_txn_id")

            # Determine unique retail zones visited (preserve visit order)
            seen_zones = set()
            zones_visited = [z for z in journey_path if not (z in seen_zones or seen_zones.add(z))]

            # Resolve associated transaction
            associated_transaction = None
            if associated_txn_id and str(associated_txn_id) in txn_map:
                t = txn_map[str(associated_txn_id)]
                associated_transaction = {
                    "transaction_id": str(_get_field(t, "id")),
                    "timestamp": _get_field(t, "timestamp"),
                    "total_amount": float(_get_field(t, "total_amount", 0.0)),
                }

            # Map matching events by timestamp window
            v_events = events_by_visitor.get(str(visitor_id), [])
            session_events_count = 0
            for e in v_events:
                ts = _get_field(e, "timestamp")
                if exited_at is not None:
                    if entered_at <= ts <= exited_at:
                        session_events_count += 1
                else:
                    if entered_at <= ts:
                        session_events_count += 1

            # Calculate session duration in milliseconds
            session_duration_ms = 0.0
            if exited_at is not None:
                session_duration_ms = (exited_at - entered_at).total_seconds() * 1000.0

            journey_list.append({
                "session_id": s_id,
                "visitor_id": str(visitor_id),
                "journey_path": journey_path,
                "entered_at": entered_at,
                "exited_at": exited_at,
                "zones_visited": zones_visited,
                "joined_billing_queue": joined_billing_queue,
                "associated_transaction": associated_transaction,
                "event_count": session_events_count,
                "session_duration_ms": round(session_duration_ms, 2),
            })

        # 4. Categorize journeys into audit segments
        longest_journeys = sorted(
            journey_list,
            key=lambda j: j["session_duration_ms"],
            reverse=True
        )[:10]

        billing_queue_no_purchase = [
            j for j in journey_list
            if j["joined_billing_queue"] and j["associated_transaction"] is None
        ]

        purchase_no_retail_zones = [
            j for j in journey_list
            if j["associated_transaction"] is not None and not j["journey_path"]
        ]

        entry_exit_only = [
            j for j in journey_list
            if not j["journey_path"] and not j["joined_billing_queue"] and j["associated_transaction"] is None
        ]

        single_zone_sessions = [
            j for j in journey_list
            if len(j["zones_visited"]) == 1
        ]

        return {
            "journeys": journey_list,
            "audit": {
                "longest_journeys": longest_journeys,
                "billing_queue_no_purchase": billing_queue_no_purchase,
                "purchase_no_retail_zones": purchase_no_retail_zones,
                "entry_exit_only": entry_exit_only,
                "single_zone_sessions": single_zone_sessions,
            }
        }
