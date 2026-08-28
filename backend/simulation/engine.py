import simpy
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class SimulationStrategy(str, Enum):
    BASELINE = "BASELINE"
    AI_ASSISTED = "AI_ASSISTED"


class SimulationStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class SimulationEngine:
    """
    SimPy discrete-event simulation engine for RAILOPTIX.
    Trains move through network sections as SimPy processes competing for
    section resources (capacity-limited).
    """

    # Real-time pacing: seconds of wall-clock time per 1 sim-minute at 1x speed.
    # At 1x: 1 sim-min = 0.5s real. At 5x: 1 sim-min = 0.1s real.
    REAL_SECONDS_PER_SIM_MIN_AT_1X: float = 0.5

    def __init__(self):
        self.env: Optional[simpy.Environment] = None
        self.status = SimulationStatus.IDLE
        self.strategy = SimulationStrategy.BASELINE
        self.scenario: Optional[dict] = None
        self.timetable: Optional[dict] = None
        self.network = None
        self.current_tick: float = 0.0
        self.speed_multiplier: float = 1.0
        self.section_resources: dict[str, simpy.Resource] = {}
        self.events: list[dict] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._completed_trains: set[str] = set()
        self._waiting_time: dict[str, float] = {}   # train_id → total minutes waited
        self._sim_start_real: Optional[datetime] = None
        self._run_id: Optional[str] = None

    # ── Load ─────────────────────────────────────────────────────────────────

    def load_scenario(self, scenario: dict, network, timetable: dict,
                      strategy: SimulationStrategy = SimulationStrategy.BASELINE) -> None:
        self.reset()
        self.scenario = scenario
        self.timetable = timetable
        self.network = network
        self.strategy = strategy
        self.env = simpy.Environment()
        self._completed_trains.clear()
        self._waiting_time.clear()
        self.events.clear()

        # Create a SimPy Resource per section (capacity from network)
        for section_id, section in network.sections.items():
            capacity = section.get("capacity", 1)
            self.section_resources[section_id] = simpy.Resource(self.env, capacity=capacity)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.status == SimulationStatus.RUNNING:
            return
        if not self.scenario or not self.env:
            raise RuntimeError("No scenario loaded. Call load_scenario() first.")

        self._stop_event.clear()
        self._sim_start_real = datetime.now(timezone.utc)
        self.status = SimulationStatus.RUNNING

        # Spawn one SimPy process per train
        from .train_agent import train_process  # local import avoids circular dep
        for train in self.scenario["trains"]:
            route_sections = self.network.get_route_sections(train["route_id"])
            tt = self.timetable.get(train["train_id"], {})
            self.env.process(
                train_process(
                    env=self.env,
                    train=train,
                    route_sections=route_sections,
                    section_resources=self.section_resources,
                    timetable=tt,
                    engine=self,
                )
            )

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        # SimPy doesn't natively support pause; we signal the run loop to stop stepping
        self.status = SimulationStatus.PAUSED
        self._stop_event.set()

    def resume(self) -> None:
        if self.status != SimulationStatus.PAUSED:
            return
        self._stop_event.clear()
        self.status = SimulationStatus.RUNNING
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def reset(self) -> None:
        self._stop_event.set()
        self.status = SimulationStatus.IDLE
        self.env = None
        self.scenario = None
        self.timetable = None
        self.section_resources.clear()
        self.events.clear()
        self._completed_trains.clear()
        self._waiting_time.clear()
        self.current_tick = 0.0
        self._run_id = None
        # NOTE: Do NOT reset the digital_twin here.
        # The scenario router owns the twin lifecycle; calling digital_twin.reset()
        # here would wipe the twin that was just loaded before the engine is configured.

    def set_speed(self, multiplier: float) -> None:
        self.speed_multiplier = max(0.25, min(multiplier, 20.0))

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        total_trains = len(self.scenario["trains"]) if self.scenario else 0
        return {
            "status": self.status.value,
            "current_tick": self.current_tick,
            "elapsed_sim_minutes": self.current_tick,
            "scenario_id": self.scenario["scenario_id"] if self.scenario else None,
            "trains_in_flight": total_trains - len(self._completed_trains),
            "completed_trains": len(self._completed_trains),
            "total_trains": total_trains,
            "speed_multiplier": self.speed_multiplier,
        }

    def get_kpis(self) -> dict:
        """Compute KPIs from the current/completed simulation run."""
        if not self.scenario:
            return {}
        total = len(self.scenario["trains"])
        completed = len(self._completed_trains)
        delays = []
        from ..services.twin.digital_twin import digital_twin
        for t in digital_twin.get_all_trains():
            delays.append(t.delay_minutes)
        avg_delay = sum(delays) / len(delays) if delays else 0.0
        total_wait = sum(self._waiting_time.values())
        return {
            "throughput": completed,
            "average_delay": round(avg_delay, 2),
            "waiting_time": round(total_wait, 2),
            "utilization": round(completed / total, 3) if total else 0.0,
        }

    # ── Events ────────────────────────────────────────────────────────────────

    def emit_event(self, event_type: str, train_id: str, data: dict) -> None:
        event = {
            "type": event_type,
            "train_id": train_id,
            "tick": self.current_tick,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self.events.append(event)

        # Mirror into Digital Twin (local import avoids circular dependency)
        from ..services.twin.digital_twin import digital_twin
        if event_type == "SECTION_ENTER":
            digital_twin.update_train_state(
                train_id, current_section=data.get("section_id"),
                status="EN_ROUTE", direction=data.get("direction")
            )
            digital_twin.update_section_occupancy(data["section_id"], train_id, entering=True)

        elif event_type == "SECTION_EXIT":
            digital_twin.update_section_occupancy(data["section_id"], train_id, entering=False)

        elif event_type == "ARRIVAL":
            digital_twin.update_train_state(
                train_id, current_node=data.get("node_id"),
                current_section=None, status="AT_STATION",
                delay_minutes=data.get("delay_minutes", 0),
                next_station=data.get("next_station"),
            )

        elif event_type == "COMPLETED":
            digital_twin.update_train_state(train_id, status="COMPLETED", journey_progress=1.0)
            self._completed_trains.add(train_id)

        elif event_type == "HELD":
            digital_twin.update_train_state(train_id, status="HELD")
            self._waiting_time[train_id] = (
                self._waiting_time.get(train_id, 0) + data.get("wait_minutes", 0)
            )

    # ── Internal run loop ─────────────────────────────────────────────────────

    def _run(self) -> None:
        """Step the SimPy environment with real-time pacing.

        Pacing formula:
          wall_sleep = (delta_sim_minutes * REAL_SECONDS_PER_SIM_MIN_AT_1X) / speed_multiplier

        At 1x speed: 1 sim-min ≈ 0.5s real → 600 sim-min ≈ 5 minutes real.
        At 5x speed: 1 sim-min ≈ 0.1s real → 600 sim-min ≈ 1 minute real.
        """
        import time
        total_trains = len(self.scenario["trains"]) if self.scenario else 0

        while not self._stop_event.is_set():
            if len(self._completed_trains) >= total_trains:
                self.status = SimulationStatus.COMPLETED
                break

            if self.env.peek() == float("inf"):
                self.status = SimulationStatus.COMPLETED
                break

            try:
                prev_tick = self.env.now
                self.env.step()
                self.current_tick = self.env.now
                delta_sim_minutes = max(0.0, self.current_tick - prev_tick)

                # Wall-clock pacing so the frontend can see trains move in real-time
                if delta_sim_minutes > 0:
                    pace = self.REAL_SECONDS_PER_SIM_MIN_AT_1X / max(0.25, self.speed_multiplier)
                    sleep_duration = delta_sim_minutes * pace
                    # Cap max sleep per step to keep UI responsive
                    time.sleep(min(sleep_duration, 2.0))
            except Exception:
                break


# Singleton
simulation_engine = SimulationEngine()
