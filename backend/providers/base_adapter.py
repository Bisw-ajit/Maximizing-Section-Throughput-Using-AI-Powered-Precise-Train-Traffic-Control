from abc import ABC, abstractmethod
from datetime import datetime


class BaseTrainAdapter(ABC):
    """Abstract base — all provider adapters must implement this interface."""

    @abstractmethod
    async def fetch_trains(self, train_numbers: list[str] | None = None) -> list[dict]:
        """Fetch and return a list of NormalizedTrainRecord dicts."""
        ...

    def make_record(
        self,
        train_id: str,
        train_number: str,
        name: str,
        current_node: str | None,
        current_section: str | None,
        delay_minutes: float,
        next_station: str | None,
        route_id: str | None,
        is_live: bool,
        source: str,
        last_updated: datetime,
        staleness_seconds: float = 0.0,
        status: str = "EN_ROUTE",
    ) -> dict:
        return {
            "train_id": train_id,
            "train_number": train_number,
            "name": name,
            "current_node": current_node,
            "current_section": current_section,
            "delay_minutes": delay_minutes,
            "next_station": next_station,
            "route_id": route_id,
            "is_live": is_live,
            "source": source,
            "last_updated": last_updated.isoformat(),
            "staleness_seconds": staleness_seconds,
            "status": status,
        }
