from datetime import datetime, timezone
from typing import Any

from app.repositories.session_repository import SessionRepository
from app.services.anomaly_engine import AnomalyEngine


class AnomalyService:
    """Service orchestrating visitor sessions loading and anomaly detection."""

    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo

    async def get_store_anomalies(
        self,
        store_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Orchestrates database queries and runs anomaly detection."""
        sessions = await self.session_repo.get_by_store_and_timerange(
            store_id, start_time, end_time
        )
        
        evaluation_time = end_time
        if evaluation_time is None:
            # Fall back to timezone-aware UTC datetime
            evaluation_time = datetime.now(timezone.utc)
            
        anomalies = AnomalyEngine.detect_anomalies(sessions, evaluation_time=evaluation_time)
        return anomalies
