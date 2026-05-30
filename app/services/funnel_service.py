from datetime import datetime
from typing import Any

from app.repositories.session_repository import SessionRepository
from app.services.conversion_engine import ConversionEngine


class FunnelService:
    """Service orchestrating customer funnel analytics calculations."""

    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo

    async def get_store_funnel(
        self,
        store_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Fetches visitor sessions and formats conversion funnel report."""
        sessions = await self.session_repo.get_by_store_and_timerange(
            store_id, start_time, end_time
        )
        steps = ConversionEngine.calculate_funnel_steps(sessions)
        return {
            "store_id": store_id,
            "start_time": start_time,
            "end_time": end_time,
            "steps": steps,
        }
