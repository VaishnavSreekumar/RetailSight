from abc import ABC, abstractmethod
from typing import Any


class BaseRetailAnalyticsEngine(ABC):
    """Abstract base class representing the retail analytics engine interface."""

    def __init__(self, engine_name: str, version: str):
        self.engine_name = engine_name
        self.version = version

    @abstractmethod
    def process_events(self, events: list[Any]) -> Any:
        """Processes retail tracking events to compute behaviors or metrics."""
        pass
