from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from enum import Enum
from typing import Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DataSource(str, Enum):
    LIVE = "LIVE"
    RECENTLY_UPDATED = "RECENTLY_UPDATED"
    STALE = "STALE"
    SIMULATION = "SIMULATION"


STALENESS_LIVE_THRESHOLD = 60       # seconds → LIVE
STALENESS_RECENT_THRESHOLD = 300    # seconds → RECENTLY_UPDATED
# > 300s → STALE


@dataclass
class TrainState:
    train_id: str
    train_number: str
    name: str
    priority: int
    route_id: str
    status: str = "SCHEDULED"
    current_node: Optional[str] = None
    current_section: Optional[str] = None
    direction: Optional[str] = None
    delay_minutes: float = 0.0
    next_station: Optional[str] = None
    last_updated: datetime = field(default_factory=utc_now)
    data_source: DataSource = DataSource.SIMULATION
    is_live: bool = False
    staleness_seconds: float = 0.0
    journey_progress: float = 0.0   # 0.0 → 1.0


class DigitalTwin:
    """Thread-safe in-memory state manager for the RAILOPTIX railway network."""

    def __init__(self):
        self._lock = Lock()
        self._trains: dict[str, TrainState] = {}
        self._section_occupancy: dict[str, list[str]] = {}   # section_id → [train_ids]
        self._timetable: dict[str, dict] = {}                # train_id → {node_id → {scheduled_arrival, scheduled_departure}}
        self._scenario_id: Optional[str] = None
        self._last_sync: Optional[datetime] = None
        self._scenario_data: Optional[dict] = None

    # ── Scenario Loading ─────────────────────────────────────────────────────

    def load_scenario(self, scenario: dict, timetable: dict) -> None:
        """Initialise twin from a loaded scenario dict and pre-computed timetable."""
        with self._lock:
            self._trains.clear()
            self._section_occupancy.clear()
            self._timetable = timetable
            self._scenario_id = scenario["scenario_id"]
            self._scenario_data = scenario
            self._last_sync = utc_now()

            for train_data in scenario["trains"]:
                tid = train_data["train_id"]
                self._trains[tid] = TrainState(
                    train_id=tid,
                    train_number=train_data["train_number"],
                    name=train_data["name"],
                    priority=train_data["priority"],
                    route_id=train_data["route_id"],
                    current_node=train_data["initial_node"],
                    status="SCHEDULED",
                    data_source=DataSource.SIMULATION,
                    is_live=False,
                )

    # ── Live Data Updates ────────────────────────────────────────────────────

    def update_from_live(self, records: list[dict]) -> None:
        """Merge live provider records into twin state."""
        now = utc_now()
        with self._lock:
            self._last_sync = now
            for rec in records:
                tid = rec.get("train_id")
                if not tid or tid not in self._trains:
                    continue
                train = self._trains[tid]
                train.current_node = rec.get("current_node", train.current_node)
                train.current_section = rec.get("current_section", train.current_section)
                train.delay_minutes = rec.get("delay_minutes", train.delay_minutes)
                train.next_station = rec.get("next_station", train.next_station)
                train.status = rec.get("status", train.status)
                train.last_updated = utc_now()
                train.is_live = rec.get("is_live", False)
                train.staleness_seconds = rec.get("staleness_seconds", 0.0)
                train.data_source = self._compute_source(train)

    def update_train_state(self, train_id: str, **kwargs) -> None:
        """Update arbitrary fields on a train (thread-safe). Used by simulation engine."""
        with self._lock:
            train = self._trains.get(train_id)
            if not train:
                return
            for key, value in kwargs.items():
                if hasattr(train, key):
                    setattr(train, key, value)
            train.last_updated = utc_now()

    # ── Section Occupancy ────────────────────────────────────────────────────

    def update_section_occupancy(self, section_id: str, train_id: str, entering: bool) -> None:
        with self._lock:
            occupants = self._section_occupancy.setdefault(section_id, [])
            if entering and train_id not in occupants:
                occupants.append(train_id)
            elif not entering and train_id in occupants:
                occupants.remove(train_id)

    def get_section_occupancy(self) -> dict[str, list[str]]:
        with self._lock:
            return {k: list(v) for k, v in self._section_occupancy.items()}

    # ── Reads ────────────────────────────────────────────────────────────────

    def get_train(self, train_id: str) -> Optional[TrainState]:
        with self._lock:
            return self._trains.get(train_id)

    def get_all_trains(self) -> list[TrainState]:
        with self._lock:
            return list(self._trains.values())

    def get_state(self) -> dict:
        with self._lock:
            return {
                "scenario_id": self._scenario_id,
                "last_sync": self._last_sync.isoformat() if self._last_sync else None,
                "trains": [self._train_to_dict(t) for t in self._trains.values()],
                "section_occupancy": {k: list(v) for k, v in self._section_occupancy.items()},
                "train_count": len(self._trains),
            }

    def get_scheduled_time(self, train_id: str, node_id: str) -> Optional[datetime]:
        tt = self._timetable.get(train_id, {})
        node_tt = tt.get(node_id)
        if node_tt:
            return node_tt.get("scheduled_arrival") or node_tt.get("scheduled_departure")
        return None

    # ── Reset ────────────────────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            self._trains.clear()
            self._section_occupancy.clear()
            self._timetable.clear()
            self._scenario_id = None
            self._last_sync = None
            self._scenario_data = None

    # ── Internals ────────────────────────────────────────────────────────────

    def _compute_source(self, train: TrainState) -> DataSource:
        if not train.is_live:
            return DataSource.SIMULATION
        age = (utc_now() - train.last_updated).total_seconds()
        if age <= STALENESS_LIVE_THRESHOLD:
            return DataSource.LIVE
        if age <= STALENESS_RECENT_THRESHOLD:
            return DataSource.RECENTLY_UPDATED
        return DataSource.STALE

    def _train_to_dict(self, t: TrainState) -> dict:
        return {
            "train_id": t.train_id,
            "train_number": t.train_number,
            "name": t.name,
            "priority": t.priority,
            "current_node": t.current_node,
            "current_section": t.current_section,
            "direction": t.direction,
            "status": t.status,
            "delay_minutes": t.delay_minutes,
            "next_station": t.next_station,
            "route_id": t.route_id,
            "last_updated": t.last_updated.isoformat(),
            "data_source": t.data_source.value,
            "is_live": t.is_live,
            "staleness_seconds": t.staleness_seconds,
            "journey_progress": t.journey_progress,
        }


# Singleton
digital_twin = DigitalTwin()
