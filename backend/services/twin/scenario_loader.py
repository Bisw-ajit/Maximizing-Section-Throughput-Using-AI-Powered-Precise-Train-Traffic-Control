import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class ScenarioLoadError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ScenarioLoader:
    SCENARIO_DIR = Path("scenarios")

    def list_scenarios(self) -> list[dict]:
        """Scan scenarios directory and return metadata for all scenario files."""
        scenarios = []
        for f in sorted(self.SCENARIO_DIR.glob("scenario_*.json")):
            try:
                data = json.loads(f.read_text())
                scenarios.append({
                    "scenario_id": data["scenario_id"],
                    "name": data["name"],
                    "description": data.get("description", ""),
                    "network_id": data.get("network_id", "railoptix_main"),
                    "train_count": len(data.get("trains", [])),
                    "difficulty": data.get("difficulty", "MEDIUM"),
                    "file": str(f),
                })
            except Exception:
                continue
        return scenarios

    def load(self, scenario_id: str, network) -> dict:
        """Load and validate a scenario by ID. Returns the scenario dict."""
        scenario_file = self._find_file(scenario_id)
        if not scenario_file:
            raise ScenarioLoadError("SCENARIO_NOT_FOUND", f"Scenario '{scenario_id}' not found.")

        try:
            scenario = json.loads(scenario_file.read_text())
        except json.JSONDecodeError as e:
            raise ScenarioLoadError("INVALID_JSON", f"Scenario file is malformed: {e}")

        self._validate(scenario, network)
        return scenario

    def _find_file(self, scenario_id: str) -> Optional[Path]:
        for f in self.SCENARIO_DIR.glob("scenario_*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("scenario_id") == scenario_id:
                    return f
            except Exception:
                continue
        return None

    def _validate(self, scenario: dict, network) -> None:
        seen_ids: set[str] = set()
        trains = scenario.get("trains", [])

        if not trains:
            raise ScenarioLoadError("MISSING_TRAIN", "Scenario has no trains defined.")

        for train in trains:
            tid = train.get("train_id")
            if not tid:
                raise ScenarioLoadError("MISSING_TRAIN", "A train entry is missing 'train_id'.")

            # Duplicate ID check
            if tid in seen_ids:
                raise ScenarioLoadError("DUPLICATE_ID", f"Duplicate train_id: '{tid}'.")
            seen_ids.add(tid)

            # Route validity
            route_id = train.get("route_id")
            if not route_id or not network.get_route(route_id):
                raise ScenarioLoadError(
                    "INVALID_ROUTE",
                    f"Train '{tid}' references unknown route '{route_id}'."
                )

            # Initial node validity
            initial_node = train.get("initial_node")
            if not initial_node or not network.get_node(initial_node):
                raise ScenarioLoadError(
                    "MISSING_NETWORK_SECTION",
                    f"Train '{tid}' starts at unknown node '{initial_node}'."
                )

            # Scheduled departure parseable
            dep = train.get("scheduled_departure", "")
            try:
                datetime.strptime(dep, "%H:%M")
            except ValueError:
                raise ScenarioLoadError(
                    "INVALID_TIMETABLE",
                    f"Train '{tid}' has invalid scheduled_departure '{dep}'. Expected HH:MM."
                )

    def compute_timetable(self, scenario: dict, network) -> dict:
        """
        Compute per-train arrival/departure times at every node along their route.
        Returns: {train_id: {node_id: {'scheduled_arrival': datetime, 'scheduled_departure': datetime}}}
        """
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        timetable: dict[str, dict] = {}

        for train in scenario.get("trains", []):
            tid = train["train_id"]
            route_id = train["route_id"]
            avg_speed = train.get("avg_speed_kmh", 70)
            dwell_times: dict[str, int] = train.get("dwell_time_minutes", {})

            # Parse departure time
            h, m = map(int, train["scheduled_departure"].split(":"))
            current_time = today + timedelta(hours=h, minutes=m)

            route = network.get_route(route_id)
            if not route:
                continue

            node_sequence = route["node_sequence"]
            train_timetable: dict[str, dict] = {}

            for i, node_id in enumerate(node_sequence):
                arrival = current_time
                dwell = dwell_times.get(node_id, 2)
                departure = arrival + timedelta(minutes=dwell)

                train_timetable[node_id] = {
                    "scheduled_arrival": arrival,
                    "scheduled_departure": departure,
                }

                # Advance time to next node
                if i < len(node_sequence) - 1:
                    next_node = node_sequence[i + 1]
                    section = network.get_section_between(node_id, next_node)
                    if section:
                        travel_minutes = (section["length_km"] / avg_speed) * 60
                        current_time = departure + timedelta(minutes=travel_minutes)
                    else:
                        current_time = departure + timedelta(minutes=30)  # fallback

            timetable[tid] = train_timetable

        return timetable


# Singleton
scenario_loader = ScenarioLoader()
