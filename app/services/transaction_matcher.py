from datetime import datetime, timedelta
from typing import Any, Sequence
import structlog

logger = structlog.get_logger()


def _get_field(obj: Any, attr: str, default: Any = None) -> Any:
    """Helper to retrieve attributes from either objects or dicts."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


class TransactionMatcher:
    """Service evaluating matches between visitor sessions and point of sale transactions."""

    @classmethod
    def evaluate_match(cls, session: Any, transaction: Any) -> dict[str, Any]:
        """Calculates detailed match statistics and scoring for a session-transaction candidate pair."""
        session_id = _get_field(session, "id")
        transaction_id = _get_field(transaction, "id")
        
        entered_at = _get_field(session, "entered_at")
        exited_at = _get_field(session, "exited_at")
        txn_timestamp = _get_field(transaction, "timestamp")
        
        # 1. Enforce time window compatibility check
        # Transaction must occur after entry, up to exited_at + 10 mins (or +2 hours if exited_at is missing)
        start_window = entered_at
        end_window = (
            exited_at + timedelta(minutes=10)
            if exited_at
            else entered_at + timedelta(hours=2)
        )
        
        within_time_window = start_window <= txn_timestamp <= end_window
        
        # 2. Check billing queue indicator
        joined_billing_queue = bool(_get_field(session, "has_joined_billing_queue", False))
        
        # 3. Calculate absolute time difference in seconds
        reference_time = exited_at if exited_at else entered_at
        time_distance_seconds = abs((txn_timestamp - reference_time).total_seconds())
        
        # 4. Calculate decay score
        if not within_time_window:
            final_match_score = 0.0
        else:
            time_difference_minutes = time_distance_seconds / 60.0
            base_score = 100.0 / (1.0 + time_difference_minutes)
            
            # Apply billing queue presence multiplier (1.0 if joined queue, 0.3 if missed/unregistered)
            multiplier = 1.0 if joined_billing_queue else 0.3
            final_match_score = round(base_score * multiplier, 2)
            
        # 5. Map match confidence levels
        if final_match_score >= 80.0:
            match_confidence = "HIGH"
        elif final_match_score >= 50.0:
            match_confidence = "MEDIUM"
        else:
            match_confidence = "LOW"
            
        return {
            "session_id": session_id,
            "transaction_id": transaction_id,
            "within_time_window": within_time_window,
            "joined_billing_queue": joined_billing_queue,
            "time_distance_seconds": round(time_distance_seconds, 2),
            "final_match_score": final_match_score,
            "match_confidence": match_confidence,
        }

    @classmethod
    def match_cohort(cls, sessions: Sequence[Any], transactions: Sequence[Any]) -> dict[str, list]:
        """Runs greedy attribution matching across cohorts of sessions and transactions."""
        # 1. Compute scores for all candidate pairs
        all_candidates = []
        for session in sessions:
            for txn in transactions:
                diag = cls.evaluate_match(session, txn)
                if diag["within_time_window"] and diag["final_match_score"] > 0.0:
                    all_candidates.append((diag, session, txn))
                    
        # Sort candidates descending by match score
        all_candidates.sort(key=lambda x: x[0]["final_match_score"], reverse=True)
        
        matched_session_ids = set()
        matched_txn_ids = set()
        
        matched_pairs = []
        
        # 2. Greedily match pairs
        for diag, session, txn in all_candidates:
            s_id = diag["session_id"]
            t_id = diag["transaction_id"]
            
            if s_id not in matched_session_ids and t_id not in matched_txn_ids:
                matched_session_ids.add(s_id)
                matched_txn_ids.add(t_id)
                
                matched_pairs.append({
                    "session_id": str(s_id),
                    "transaction_id": str(t_id),
                    "match_score": diag["final_match_score"],
                    "match_confidence": diag["match_confidence"],
                })
                
                logger.info(
                    "Attributed transaction to visitor session",
                    session_id=str(s_id),
                    transaction_id=str(t_id),
                    score=diag["final_match_score"],
                    confidence=diag["match_confidence"],
                )
                
        # 3. Categorize unmatched records with diagnostic reasons
        unmatched_sessions = []
        for session in sessions:
            s_id = _get_field(session, "id")
            if s_id not in matched_session_ids:
                reason = "No compatible transaction found within time window"
                if not _get_field(session, "has_joined_billing_queue", False):
                    reason = "Visitor did not join the checkout billing queue (score multiplier reduced)"
                
                unmatched_sessions.append({
                    "session_id": str(s_id),
                    "visitor_id": _get_field(session, "visitor_id"),
                    "entered_at": _get_field(session, "entered_at").isoformat(),
                    "exited_at": _get_field(session, "exited_at").isoformat() if _get_field(session, "exited_at") else None,
                    "joined_billing_queue": bool(_get_field(session, "has_joined_billing_queue")),
                    "reason": reason,
                })
                
                logger.info(
                    "Session remaining unmatched",
                    session_id=str(s_id),
                    visitor_id=_get_field(session, "visitor_id"),
                    reason=reason,
                )
                
        unmatched_transactions = []
        for txn in transactions:
            t_id = _get_field(txn, "id")
            if t_id not in matched_txn_ids:
                reason = "No session matched within time window or queue criteria"
                unmatched_transactions.append({
                    "transaction_id": str(t_id),
                    "timestamp": _get_field(txn, "timestamp").isoformat(),
                    "total_amount": float(_get_field(txn, "total_amount", 0.0)),
                    "reason": reason,
                })
                
                logger.info(
                    "Transaction remaining unmatched",
                    transaction_id=str(t_id),
                    timestamp=_get_field(txn, "timestamp").isoformat(),
                    reason=reason,
                )
                
        return {
            "matched": matched_pairs,
            "unmatched_sessions": unmatched_sessions,
            "unmatched_transactions": unmatched_transactions,
        }
