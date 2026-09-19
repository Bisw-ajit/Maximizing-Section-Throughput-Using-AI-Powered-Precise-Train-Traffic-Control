"""
RAILOPTIX — Siding & Loop Line Capacity Optimizer
=================================================
Manages and optimizes station loop line / siding capacity allocation,
evaluates headroom across the Cuttack-Khurda-Puri/Brahmapur corridor,
and proactively prevents secondary deadlocks during junction saturation.

Fulfills: JIRA RAIL-16.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

from ..twin.digital_twin import digital_twin
from ..twin.network_graph import rail_network
from ..decision.action_generator import CandidateAction, ActionType


# Nominal siding/loop line capacities across ECoR stations
DEFAULT_STATION_CAPACITIES: Dict[str, int] = {
    "CTK": 4,     # Cuttack: 4 platforms
    "BGBR": 2,    # Barang: 2 passing loops
    "BBS": 6,     # Bhubaneswar: 6 platforms
    "RET": 2,     # Retang: 2 loops
    "KUR": 6,     # Khurda Road Junction: 4 passenger platforms + 2 freight loops
    "SIL": 2,     # Sakhigopal: 2 crossing loops (single-line junction buffer)
    "PURI": 8,    # Puri Terminal: 8 platforms
    "BALU": 2,    # Balugaon: 2 passing loops
    "KLK": 2,     # Khallikote: 2 passing loops
    "CAP": 2,     # Chatrapur: 2 passing loops
    "BAM": 4,     # Brahmapur: 4 platforms
}


@dataclass
class StationSidingInfo:
    station_id: str
    station_name: str
    total_capacity: int
    occupied_count: int
    available_headroom: int
    utilization_pct: float
    is_congested: bool
    is_saturated: bool
    occupying_trains: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self.station_id,
            "station_name": self.station_name,
            "total_capacity": self.total_capacity,
            "occupied_count": self.occupied_count,
            "available_headroom": self.available_headroom,
            "utilization_pct": round(self.utilization_pct, 1),
            "is_congested": self.is_congested,
            "is_saturated": self.is_saturated,
            "occupying_trains": self.occupying_trains,
        }


class SidingOptimizer:
    """
    Evaluates and enforces siding/loop capacity constraints, prevents
    secondary deadlocks, and identifies upstream relocation buffers.
    """

    def __init__(self, capacities: Optional[Dict[str, int]] = None):
        self.capacities = capacities or dict(DEFAULT_STATION_CAPACITIES)
        # Dynamic occupancy overrides for simulation/what-if evaluation
        self._manual_occupancy: Dict[str, set[str]] = {k: set() for k in self.capacities}

    def reset_occupancy(self) -> None:
        """Clear dynamic occupancy overrides."""
        self._manual_occupancy = {k: set() for k in self.capacities}

    def record_train_presence(self, station_id: str, train_id: str) -> None:
        """Register train presence at station loop/platform."""
        if station_id in self._manual_occupancy:
            self._manual_occupancy[station_id].add(train_id)

    def release_train_presence(self, station_id: str, train_id: str) -> None:
        """Release train occupancy from station loop/platform."""
        if station_id in self._manual_occupancy:
            self._manual_occupancy[station_id].discard(train_id)

    def get_current_occupancy(self, station_id: str) -> List[str]:
        """Get set of trains currently residing/dwelling at station."""
        occupants = set(self._manual_occupancy.get(station_id, set()))
        # Also incorporate digital twin train positions if matched
        for train in digital_twin.get_all_trains():
            if train.current_node == station_id or train.current_section == station_id:
                occupants.add(train.train_id)
        return sorted(list(occupants))

    def get_station_status(self, station_id: str) -> StationSidingInfo:
        """Calculate real-time capacity and headroom for a specific station."""
        node = rail_network.get_node(station_id)
        if isinstance(node, dict):
            st_name = node.get("name", station_id)
        elif node:
            st_name = getattr(node, "name", station_id)
        else:
            st_name = station_id

        cap = self.capacities.get(station_id, 2)
        occupants = self.get_current_occupancy(station_id)
        occ_count = len(occupants)
        headroom = max(0, cap - occ_count)
        util_pct = min(100.0, (occ_count / cap) * 100.0) if cap > 0 else 100.0

        return StationSidingInfo(
            station_id=station_id,
            station_name=st_name,
            total_capacity=cap,
            occupied_count=occ_count,
            available_headroom=headroom,
            utilization_pct=util_pct,
            is_congested=util_pct >= 75.0,
            is_saturated=headroom == 0,
            occupying_trains=occupants,
        )

    def get_all_siding_status(self) -> Dict[str, StationSidingInfo]:
        """Return comprehensive status for all modeled stations."""
        return {st: self.get_station_status(st) for st in self.capacities}

    def check_deadlock_risk(
        self, station_id: str, additional_holds: int = 1
    ) -> Dict[str, Any]:
        """
        Assess whether holding additional train(s) creates a secondary deadlock risk.
        Secondary deadlock triggers if remaining headroom < additional_holds,
        meaning an incoming train would foul mainline clearance points.
        """
        status = self.get_station_status(station_id)
        projected_headroom = status.available_headroom - additional_holds

        if projected_headroom < 0:
            return {
                "has_risk": True,
                "risk_level": "CRITICAL",
                "reason": (
                    f"SECONDARY DEADLOCK RISK: Station {status.station_name} ({station_id}) has "
                    f"{status.occupied_count}/{status.total_capacity} sidings full. "
                    f"Holding {additional_holds} more train(s) will overflow loops into the mainline throat."
                ),
                "projected_headroom": projected_headroom,
            }
        elif projected_headroom == 0:
            return {
                "has_risk": True,
                "risk_level": "WARNING",
                "reason": (
                    f"CAPACITY WARNING: Station {status.station_name} ({station_id}) will reach "
                    f"100% saturation ({status.total_capacity}/{status.total_capacity}). Zero headroom remaining."
                ),
                "projected_headroom": 0,
            }
        else:
            return {
                "has_risk": False,
                "risk_level": "NOMINAL",
                "reason": (
                    f"Feasible: Station {status.station_name} ({station_id}) retains "
                    f"{projected_headroom} buffer loop(s) after requested hold."
                ),
                "projected_headroom": projected_headroom,
            }

    def find_alternative_upstream_siding(
        self, target_station: str, route_id: str, direction: str = "SOUTHBOUND"
    ) -> Optional[str]:
        """
        Find nearest upstream station along the specified route with available loop headroom.
        For instance, if KUR is saturated for a southbound train on route_A,
        checks RET or BBS for available hold capacity.
        """
        route = rail_network.get_route(route_id)
        if isinstance(route, dict):
            nodes = route.get("node_sequence", [])
        elif route:
            nodes = getattr(route, "node_sequence", [])
        else:
            nodes = []

        if not nodes or target_station not in nodes:
            return None

        target_idx = nodes.index(target_station)

        # Look backward (upstream) from target station
        upstream_candidates = nodes[:target_idx] if direction == "SOUTHBOUND" else nodes[target_idx + 1:]
        # Reverse to check closest upstream first
        search_order = list(reversed(upstream_candidates)) if direction == "SOUTHBOUND" else upstream_candidates

        for st in search_order:
            if st in self.capacities:
                st_status = self.get_station_status(st)
                if st_status.available_headroom >= 1:
                    return st

        return None

    def evaluate_action_siding_feasibility(
        self, action: CandidateAction
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates whether a proposed CandidateAction (e.g. HOLD_TRAIN or CROSSING_WAIT)
        can be safely accommodated without exceeding station loop capacity.
        Returns:
          - is_feasible: bool
          - rejection_reason: Optional[str]
          - recommended_relocation: Optional[str]
        """
        if action.action_type not in (ActionType.HOLD_TRAIN, ActionType.CROSSING_WAIT):
            # Prioritize or speed advisories don't occupy stationary sidings
            return True, None, None

        loc = action.parameters.get("crossing_station", action.target_location)
        deadlock = self.check_deadlock_risk(loc, additional_holds=1)

        if deadlock["risk_level"] == "CRITICAL":
            # Attempt to find alternative upstream siding
            train = digital_twin.get_train(action.target_train_id)
            alt_station = None
            if train and train.route_id:
                direction = "SOUTHBOUND" if train.direction == 1 else "NORTHBOUND"
                alt_station = self.find_alternative_upstream_siding(loc, train.route_id, direction)

            reason = deadlock["reason"]
            if alt_station:
                reason += f" Siding Optimizer recommends upstream hold relocation to {alt_station}."

            return False, reason, alt_station

        return True, None, None

    def optimize_candidate_actions(
        self, actions: List[CandidateAction]
    ) -> List[CandidateAction]:
        """
        Inspects a list of CandidateActions and either approves them,
        marks them infeasible due to secondary deadlock risk, or adapts their
        parameters to divert to safe upstream sidings.
        """
        optimized = []
        for act in actions:
            feasible, reason, alt_station = self.evaluate_action_siding_feasibility(act)
            if not feasible:
                if alt_station:
                    # Relocate action to alternative upstream station
                    new_params = dict(act.parameters)
                    new_params["original_requested_station"] = act.target_location
                    new_params["crossing_station"] = alt_station
                    relocated_action = CandidateAction(
                        action_id=f"{act.action_id}_RELOCATED_{alt_station}",
                        conflict_id=act.conflict_id,
                        action_type=act.action_type,
                        target_train_id=act.target_train_id,
                        target_train_name=act.target_train_name,
                        target_train_priority=act.target_train_priority,
                        target_location=alt_station,
                        parameters=new_params,
                        description=(
                            f"{act.description} (Optimized: Siding hold relocated from "
                            f"{act.target_location} to {alt_station} to prevent secondary deadlock)"
                        ),
                        reason=f"Siding Capacity Relief: {reason}",
                        expected_delay_impact=act.expected_delay_impact + 1.5,
                        is_feasible=True,
                    )
                    optimized.append(relocated_action)
                else:
                    # Infeasible without safe siding
                    act.is_feasible = False
                    act.reason = f"INFEASIBLE: {reason}"
                    optimized.append(act)
            else:
                optimized.append(act)

        return optimized


# Global singleton
siding_optimizer = SidingOptimizer()
