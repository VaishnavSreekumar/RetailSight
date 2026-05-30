from datetime import datetime, timezone
from typing import Any

from app.repositories.session_repository import SessionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.conversion_engine import ConversionEngine, _get_field


class MetricsService:
    """Service orchestrating visitor sessions and point of sale metrics calculations."""

    def __init__(
        self,
        session_repo: SessionRepository,
        transaction_repo: TransactionRepository,
    ):
        self.session_repo = session_repo
        self.transaction_repo = transaction_repo

    async def get_store_metrics(
        self,
        store_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Orchestrates query fetches and aggregates metrics using the ConversionEngine."""
        # Retrieve sessions and transactions from database via repositories
        sessions = await self.session_repo.get_by_store_and_timerange(
            store_id, start_time, end_time
        )

        generated_at = datetime.now(timezone.utc)

        # Delegate business logic calculations to ConversionEngine
        metrics_data = ConversionEngine.calculate_store_metrics(sessions)
        metrics_data["store_id"] = store_id
        metrics_data["generated_at"] = generated_at

        return metrics_data
