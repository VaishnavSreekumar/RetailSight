from datetime import datetime, timedelta, timezone
from typing import Sequence
import structlog

from app.models.visitor_session import VisitorSession
from app.repositories.event_repository import EventRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.session_hydrator import SessionHydrator

logger = structlog.get_logger()


class SessionHydrationService:
    """Service orchestrating raw events aggregation into sessions and transaction matching."""

    def __init__(
        self,
        event_repo: EventRepository,
        session_repo: SessionRepository,
        transaction_repo: TransactionRepository,
    ):
        self.event_repo = event_repo
        self.session_repo = session_repo
        self.transaction_repo = transaction_repo

    async def hydrate_store_sessions(self, store_id: str) -> dict:
        """Loads events for a store, hydrates sessions, performs transaction linking, and persists."""
        # 1. Load all events for the store
        # We query the database to get all event models
        from sqlalchemy import select
        stmt = select(self.event_repo.model).filter(self.event_repo.model.store_id == store_id).order_by(self.event_repo.model.timestamp)
        res = await self.event_repo.db_session.execute(stmt)
        events = res.scalars().all()

        if not events:
            logger.info("No events found to hydrate", store_id=store_id)
            return {"hydrated_count": 0, "linked_count": 0}

        # 2. Clear existing sessions and transaction links for this store to prevent duplicate states
        await self.session_repo.delete_by_store(store_id)
        await self.transaction_repo.clear_session_links_for_store(store_id)
        await self.session_repo.db_session.flush()

        # 3. Process session state transitions
        # SessionHydrator accepts either model objects or dicts
        sessions: list[VisitorSession] = SessionHydrator.hydrate_sessions(events)

        if not sessions:
            logger.info("No active sessions created during hydration", store_id=store_id)
            return {"hydrated_count": 0, "linked_count": 0}

        # 4. Retrieve all transactions for the store to perform linking
        transactions = await self.transaction_repo.get_by_store(store_id)
        # Group transactions that haven't been linked yet
        unlinked_txns = sorted(list(transactions), key=lambda t: t.timestamp)

        # 5. Link transactions to matching sessions using TransactionMatcher
        from app.services.transaction_matcher import TransactionMatcher
        
        # Add all sessions to database context
        for session in sessions:
            self.session_repo.db_session.add(session)
            
        # Flush sessions first to prevent foreign key constraint violations on transaction updates
        await self.session_repo.db_session.flush()
            
        # Match cohorts
        matching_results = TransactionMatcher.match_cohort(sessions, transactions)
        
        session_map = {str(s.id): s for s in sessions}
        txn_map = {str(t.id): t for t in transactions}
        
        linked_count = 0
        for match in matching_results["matched"]:
            s_id = match["session_id"]
            t_id = match["transaction_id"]
            
            s_obj = session_map.get(s_id)
            t_obj = txn_map.get(t_id)
            
            if s_obj and t_obj:
                s_obj.associated_txn_id = t_obj.id
                s_obj.has_converted = True
                t_obj.session_id = s_obj.id
                
                self.session_repo.db_session.add(s_obj)
                self.transaction_repo.db_session.add(t_obj)
                linked_count += 1

        # 6. Commit all changes to the database
        await self.session_repo.db_session.commit()

        logger.info(
            "Session hydration and transaction linking complete",
            store_id=store_id,
            hydrated_count=len(sessions),
            linked_count=linked_count,
        )

        return {
            "hydrated_count": len(sessions),
            "linked_count": linked_count,
        }
