# PROMPT: Create unit tests for the transaction-to-session proximity heuristic matching engine.
# CHANGES MADE: Verified matching accuracy scores correlating cashier checkout timestamps with visitor queue exit events.

from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from app.services.transaction_matcher import TransactionMatcher
from app.repositories.session_repository import SessionRepository
from app.repositories.transaction_repository import TransactionRepository


def test_evaluate_match_time_decay_and_booster() -> None:
    """Verifies that TransactionMatcher calculates correct score decay and billing queue multipliers."""
    session = {
        "id": "s0000000-0000-0000-0000-000000000001",
        "entered_at": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
        "exited_at": datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
        "has_joined_billing_queue": True,
    }
    
    # 1. Exact match at exit time -> Score should be 100 (HIGH confidence)
    txn_exact = {
        "id": "txn_001",
        "timestamp": datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
    }
    res = TransactionMatcher.evaluate_match(session, txn_exact)
    assert res["within_time_window"] is True
    assert res["joined_billing_queue"] is True
    assert res["final_match_score"] == 100.0
    assert res["match_confidence"] == "HIGH"
    
    # 2. 1 minute difference -> Score should be 100 / (1 + 1) = 50.0 (MEDIUM confidence)
    txn_1min = {
        "id": "txn_002",
        "timestamp": datetime(2026, 5, 30, 10, 11, 0, tzinfo=timezone.utc),
    }
    res = TransactionMatcher.evaluate_match(session, txn_1min)
    assert res["within_time_window"] is True
    assert res["final_match_score"] == 50.0
    assert res["match_confidence"] == "MEDIUM"

    # 3. 1 minute difference, but did NOT join billing queue -> Score should be 50.0 * 0.3 = 15.0 (LOW confidence)
    session_no_queue = session.copy()
    session_no_queue["has_joined_billing_queue"] = False
    res = TransactionMatcher.evaluate_match(session_no_queue, txn_1min)
    assert res["within_time_window"] is True
    assert res["joined_billing_queue"] is False
    assert res["final_match_score"] == 15.0
    assert res["match_confidence"] == "LOW"

    # 4. Outside time window (e.g. 15 minutes after exit) -> Score should be 0.0
    txn_far = {
        "id": "txn_003",
        "timestamp": datetime(2026, 5, 30, 10, 25, 0, tzinfo=timezone.utc),
    }
    res = TransactionMatcher.evaluate_match(session, txn_far)
    assert res["within_time_window"] is False
    assert res["final_match_score"] == 0.0
    assert res["match_confidence"] == "LOW"


def test_match_cohort_greedy_pairing() -> None:
    """Verifies that cohort matching performs greedy pairings and flags unmatched records with diagnostics."""
    store_id = "STORE_BLR_002"
    sessions = [
        # Session 1: Joined billing queue, exited at 10:10
        {
            "id": "s1",
            "visitor_id": "VIS_001",
            "entered_at": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            "exited_at": datetime(2026, 5, 30, 10, 10, 0, tzinfo=timezone.utc),
            "has_joined_billing_queue": True,
        },
        # Session 2: Exited at 10:05, did NOT join billing queue
        {
            "id": "s2",
            "visitor_id": "VIS_002",
            "entered_at": datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc),
            "exited_at": datetime(2026, 5, 30, 10, 0, 5, tzinfo=timezone.utc),
            "has_joined_billing_queue": False,
        }
    ]
    
    transactions = [
        # Transaction 1: Timestamp 10:11 (closer to session 1)
        {
            "id": "t1",
            "timestamp": datetime(2026, 5, 30, 10, 11, 0, tzinfo=timezone.utc),
            "total_amount": 100.0,
        },
        # Transaction 2: Timestamp 10:30 (outside session windows)
        {
            "id": "t2",
            "timestamp": datetime(2026, 5, 30, 10, 30, 0, tzinfo=timezone.utc),
            "total_amount": 50.0,
        }
    ]
    
    result = TransactionMatcher.match_cohort(sessions, transactions)
    
    # Session 1 matched to Transaction 1 (1 minute difference -> score 50)
    assert len(result["matched"]) == 1
    assert result["matched"][0]["session_id"] == "s1"
    assert result["matched"][0]["transaction_id"] == "t1"
    assert result["matched"][0]["match_score"] == 50.0
    
    # Session 2 remains unmatched (exited 10:00:05, t1 at 10:11:00 is outside window)
    assert len(result["unmatched_sessions"]) == 1
    assert result["unmatched_sessions"][0]["session_id"] == "s2"
    assert "did not join the checkout" in result["unmatched_sessions"][0]["reason"]
    
    # Transaction 2 remains unmatched (timestamp 10:30 is outside window)
    assert len(result["unmatched_transactions"]) == 1
    assert result["unmatched_transactions"][0]["transaction_id"] == "t2"


@pytest.mark.asyncio
async def test_transaction_matches_endpoint(client: AsyncClient, monkeypatch) -> None:
    """Verifies that the GET /stores/{store_id}/transaction-matches API works."""
    store_id = "STORE_BLR_002"
    
    mock_data = {
        "matched": [
            {"session_id": "00000000-0000-0000-0000-000000000001", "transaction_id": "txn_001", "match_score": 95.5, "match_confidence": "HIGH"}
        ],
        "unmatched_sessions": [
            {"session_id": "00000000-0000-0000-0000-000000000002", "visitor_id": "VIS_002", "entered_at": "2026-05-30T10:00:00Z", "exited_at": "2026-05-30T10:00:05Z", "joined_billing_queue": False, "reason": "No match"}
        ],
        "unmatched_transactions": [
            {"transaction_id": "txn_002", "timestamp": "2026-05-30T10:30:00Z", "total_amount": 50.0, "reason": "No match"}
        ]
    }
    
    def mock_match_cohort(*args, **kwargs):
        return mock_data
        
    async def mock_get_by_store(*args, **kwargs):
        return []
        
    monkeypatch.setattr(TransactionMatcher, "match_cohort", mock_match_cohort)
    monkeypatch.setattr(SessionRepository, "get_by_store", mock_get_by_store)
    monkeypatch.setattr(TransactionRepository, "get_by_store", mock_get_by_store)
    
    response = await client.get(f"/api/v1/stores/{store_id}/transaction-matches")
    assert response.status_code == 200
    
    res_data = response.json()
    assert len(res_data["matched"]) == 1
    assert res_data["matched"][0]["transaction_id"] == "txn_001"
    assert res_data["matched"][0]["match_confidence"] == "HIGH"
    assert len(res_data["unmatched_sessions"]) == 1
    assert len(res_data["unmatched_transactions"]) == 1
