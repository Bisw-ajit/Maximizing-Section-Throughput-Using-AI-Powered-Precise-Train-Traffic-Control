import httpx
import logging
from datetime import datetime
from ..base_adapter import BaseTrainAdapter

logger = logging.getLogger(__name__)


class RailRadarAdapter(BaseTrainAdapter):
    """
    Adapter for the RailRadar live train data provider.
    Falls back to cached state on timeout or API failure.
    """
    BASE_URL = "https://railradar.co.in/api"  # Replace with actual endpoint if available
    CACHE_TTL_SECONDS = 60

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._cache: list[dict] = []
        self._cache_time: datetime | None = None

    async def fetch_trains(self, train_numbers: list[str] | None = None) -> list[dict]:
        if self._is_cache_valid():
            logger.debug("RailRadar: returning cached data")
            return self._cache

        if not self.api_key:
            logger.warning("RailRadar: no API key configured, using cache/fallback")
            return self._cache

        try:
            params: dict = {}
            if train_numbers:
                params["trains"] = ",".join(train_numbers)

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/trains",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                raw_list = resp.json().get("data", [])
                normalized = [self.normalize(r) for r in raw_list]
                self._cache = normalized
                self._cache_time = datetime.utcnow()
                return normalized

        except (httpx.TimeoutException, httpx.HTTPError) as e:
            logger.warning(f"RailRadar fetch failed: {e}. Returning cached data.")
            return self._cache
        except Exception as e:
            logger.error(f"RailRadar unexpected error: {e}")
            return self._cache

    def normalize(self, raw: dict) -> dict:
        """Map RailRadar response fields → NormalizedTrainRecord."""
        last_updated_str = raw.get("last_updated", datetime.utcnow().isoformat())
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
        except ValueError:
            last_updated = datetime.utcnow()

        staleness = (datetime.utcnow() - last_updated).total_seconds()

        return self.make_record(
            train_id=str(raw.get("train_number", raw.get("id", ""))),
            train_number=str(raw.get("train_number", "")),
            name=raw.get("name", raw.get("train_name", "Unknown")),
            current_node=raw.get("current_station_code"),
            current_section=None,
            delay_minutes=float(raw.get("delay", raw.get("delay_minutes", 0))),
            next_station=raw.get("next_station_code"),
            route_id=None,  # RailRadar doesn't provide our route IDs — mapped separately
            is_live=True,
            source="railradar",
            last_updated=last_updated,
            staleness_seconds=staleness,
            status=raw.get("status", "EN_ROUTE"),
        )

    def _is_cache_valid(self) -> bool:
        if not self._cache_time:
            return False
        return (datetime.utcnow() - self._cache_time).total_seconds() < self.CACHE_TTL_SECONDS


class ScenarioFallbackAdapter(BaseTrainAdapter):
    """
    Returns controlled scenario state from the Digital Twin
    when the live provider is unavailable.
    """

    def __init__(self, twin):
        self.twin = twin

    async def fetch_trains(self, train_numbers: list[str] | None = None) -> list[dict]:
        trains = self.twin.get_all_trains()
        now = datetime.utcnow()
        records = []
        for t in trains:
            if train_numbers and t.train_number not in train_numbers:
                continue
            records.append(self.make_record(
                train_id=t.train_id,
                train_number=t.train_number,
                name=t.name,
                current_node=t.current_node,
                current_section=t.current_section,
                delay_minutes=t.delay_minutes,
                next_station=t.next_station,
                route_id=t.route_id,
                is_live=False,
                source="scenario_fallback",
                last_updated=now,
                staleness_seconds=0.0,
                status=t.status,
            ))
        return records
