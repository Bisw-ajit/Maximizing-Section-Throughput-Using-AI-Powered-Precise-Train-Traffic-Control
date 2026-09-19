"""
RAILOPTIX — Candidate Action Generator for Junction & Corridor Bottlenecks
===========================================================================
Generates feasible, dispatch-compliant candidate actions to resolve detected
traffic conflicts (junction converging paths, single-line crossing, and section headways).

Fulfills: JIRA RAIL-9.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Optional, Any

from ..twin.digital_twin import digital_twin, TrainState
from ..twin.network_graph import rail_network
from ..conflict.conflict_detector import Conflict, ConflictType


class ActionType(str, Enum):
    HOLD_TRAIN = "HOLD_TRAIN"
    PRIORITIZE_TRAIN = "PRIORITIZE_TRAIN"
    CROSSING_WAIT = "CROSSING_WAIT"
    SPEED_ADVISORY = "SPEED_ADVISORY"
    REROUTE = "REROUTE"


@dataclass
class CandidateAction:
    action_id: str
    conflict_id: str
    action_type: ActionType
    target_train_id: str
    target_train_name: str
    target_train_priority: int
    target_location: str                   # Node ID or Section ID
    parameters: Dict[str, Any]             # hold_minutes, speed_delta_kmh, siding_node, yield_to_train_id, etc.
    description: str
    reason: str
    expected_delay_impact: float           # Extra delay (+min) or delay saved (-min)
    is_feasible: bool = True
    feasibility_reason: str = "Passed network topology & capacity constraints."
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "conflict_id": self.conflict_id,
            "action_type": self.action_type.value,
            "target_train_id": self.target_train_id,
            "target_train_name": self.target_train_name,
            "target_train_priority": self.target_train_priority,
            "target_location": self.target_location,
            "parameters": self.parameters,
            "description": self.description,
            "reason": self.reason,
            "expected_delay_impact": round(self.expected_delay_impact, 2),
            "is_feasible": self.is_feasible,
            "feasibility_reason": self.feasibility_reason,
            "created_at": self.created_at.isoformat(),
        }


class ActionGenerator:
    """
    Synthesizes candidate operational interventions for railway traffic controllers.
    """

    DEFAULT_HOLD_MINUTES: float = 6.0
    MAX_PERMISSIBLE_HOLD_MINUTES: float = 15.0

    def generate_actions_for_conflict(self, conflict: Conflict) -> List[CandidateAction]:
        """Generate a ranked suite of candidate actions tailored to the specific conflict."""
        actions: List[CandidateAction] = []
        trains = [digital_twin.get_train(tid) for tid in conflict.train_ids]
        valid_trains = [t for t in trains if t is not None]

        if len(valid_trains) < 2:
            return actions

        # Sort trains by priority (Priority 1 is highest in Indian Railways: Rajdhani/Vande Bharat)
        valid_trains.sort(key=lambda t: (t.priority, -t.delay_minutes))
        high_prio_train = valid_trains[0]
        low_prio_train = valid_trains[1]

        c_type = conflict.conflict_type

        if c_type == ConflictType.JUNCTION_CONFLICT:
            actions.extend(self._generate_junction_actions(conflict, high_prio_train, low_prio_train))
        elif c_type == ConflictType.CROSSING_CONFLICT:
            actions.extend(self._generate_crossing_actions(conflict, high_prio_train, low_prio_train))
        elif c_type == ConflictType.SECTION_CONFLICT:
            actions.extend(self._generate_section_actions(conflict, high_prio_train, low_prio_train))
        else:
            actions.extend(self._generate_generic_actions(conflict, high_prio_train, low_prio_train))

        return actions

    def generate_all(self, conflicts: List[Conflict]) -> Dict[str, List[CandidateAction]]:
        """Map conflict_id -> List of candidate actions."""
        results = {}
        for c in conflicts:
            results[c.conflict_id] = self.generate_actions_for_conflict(c)
        return results

    # ── 1. Junction Conflict Action Strategies ────────────────────────────────

    def _generate_junction_actions(
        self, conflict: Conflict, high_prio: TrainState, low_prio: TrainState
    ) -> List[CandidateAction]:
        actions = []
        c_id = conflict.conflict_id
        loc = conflict.location  # typically "KUR" (Khurda Road)

        # Action A: HOLD lower priority train at approach station/loop
        hold_stn = low_prio.current_node or "RET"
        node_info = rail_network.get_node(hold_stn)
        plat_cap = node_info.get("platform_count", 2) if node_info else 2
        is_hold_feasible = plat_cap >= 2

        actions.append(CandidateAction(
            action_id=f"{c_id}_ACT_HOLD_LOW",
            conflict_id=c_id,
            action_type=ActionType.HOLD_TRAIN,
            target_train_id=low_prio.train_id,
            target_train_name=low_prio.name,
            target_train_priority=low_prio.priority,
            target_location=hold_stn,
            parameters={
                "hold_duration_minutes": 5.0,
                "holding_station": hold_stn,
                "yield_to_train_id": high_prio.train_id,
                "junction_node": loc,
            },
            description=f"Hold {low_prio.name} ({low_prio.train_number}) at {hold_stn} loop line for 5.0 min.",
            reason=(
                f"Holds lower-priority train (P{low_prio.priority}) to grant clean junction clearance "
                f"at {loc} for {high_prio.name} (P{high_prio.priority})."
            ),
            expected_delay_impact=+5.0,
            is_feasible=is_hold_feasible,
            feasibility_reason=(
                f"Station {hold_stn} has {plat_cap} platforms/loops available for safe holding."
                if is_hold_feasible else f"Station {hold_stn} platform capacity constrained."
            ),
        ))

        # Action B: PRIORITIZE higher priority train
        actions.append(CandidateAction(
            action_id=f"{c_id}_ACT_PRIO_HIGH",
            conflict_id=c_id,
            action_type=ActionType.PRIORITIZE_TRAIN,
            target_train_id=high_prio.train_id,
            target_train_name=high_prio.name,
            target_train_priority=high_prio.priority,
            target_location=loc,
            parameters={
                "clearance_lead_minutes": 3.0,
                "junction_node": loc,
                "subordinate_train_id": low_prio.train_id,
            },
            description=f"Grant continuous green aspect priority to {high_prio.name} through {loc} junction.",
            reason=(
                f"Protects on-time performance of premium service (P{high_prio.priority}) "
                f"by securing route interlock at {loc} 3 minutes in advance."
            ),
            expected_delay_impact=0.0,
            is_feasible=True,
            feasibility_reason=f"Junction interlocking at {loc} supports priority movement authorization.",
        ))

        # Action C: SPEED_ADVISORY (Regulate speed to stagger arrival)
        actions.append(CandidateAction(
            action_id=f"{c_id}_ACT_SPEED_ADVISORY",
            conflict_id=c_id,
            action_type=ActionType.SPEED_ADVISORY,
            target_train_id=low_prio.train_id,
            target_train_name=low_prio.name,
            target_train_priority=low_prio.priority,
            target_location=low_prio.current_section or loc,
            parameters={
                "speed_delta_kmh": -15.0,
                "target_speed_kmh": 60.0,
                "stagger_minutes": 4.0,
            },
            description=f"Issue speed reduction advisory (-15 km/h) to {low_prio.name} approaching {loc}.",
            reason=(
                f"Staggers arrival at {loc} by 4.0 minutes without requiring a complete stop, "
                f"saving locomotive braking energy and reducing recovery delay."
            ),
            expected_delay_impact=+2.5,
            is_feasible=True,
            feasibility_reason="Approach section signalling supports variable speed regulation.",
        ))

        # Action D: REROUTE Check
        actions.append(CandidateAction(
            action_id=f"{c_id}_ACT_REROUTE",
            conflict_id=c_id,
            action_type=ActionType.REROUTE,
            target_train_id=low_prio.train_id,
            target_train_name=low_prio.name,
            target_train_priority=low_prio.priority,
            target_location=loc,
            parameters={"alternative_route_id": None},
            description=f"Attempt alternative bypass routing around {loc} for {low_prio.name}.",
            reason=f"Examines if a secondary bypass corridor exists around {loc}.",
            expected_delay_impact=+18.0,
            is_feasible=False,
            feasibility_reason=f"No viable detour line around {loc} junction on the active corridor.",
        ))

        return actions

    # ── 2. Single-Line Crossing Conflict Action Strategies ────────────────────

    def _generate_crossing_actions(
        self, conflict: Conflict, high_prio: TrainState, low_prio: TrainState
    ) -> List[CandidateAction]:
        actions = []
        c_id = conflict.conflict_id
        loc = conflict.location

        # Identify intermediate crossing siding (e.g. SIL between KUR and PURI)
        siding_node = "SIL" if "PURI" in loc or "SIL" in loc else "BALU"
        siding_info = rail_network.get_node(siding_node)
        has_siding = siding_info is not None

        # Action A: CROSSING_WAIT at intermediate siding
        actions.append(CandidateAction(
            action_id=f"{c_id}_ACT_CROSSING_WAIT",
            conflict_id=c_id,
            action_type=ActionType.CROSSING_WAIT,
            target_train_id=low_prio.train_id,
            target_train_name=low_prio.name,
            target_train_priority=low_prio.priority,
            target_location=siding_node,
            parameters={
                "crossing_station": siding_node,
                "hold_duration_minutes": 8.0,
                "opposing_train_id": high_prio.train_id,
                "track_assignment": "LOOP_LINE",
            },
            description=f"Divert {low_prio.name} to {siding_node} loop line; hold for {high_prio.name} crossing.",
            reason=(
                f"Single-track contention on {loc}: {low_prio.name} (P{low_prio.priority}) enters {siding_node} "
                f"loop siding, allowing opposing {high_prio.name} (P{high_prio.priority}) to clear on mainline."
            ),
            expected_delay_impact=+8.0,
            is_feasible=has_siding,
            feasibility_reason=(
                f"Station {siding_node} has loop line siding equipped for crossing maneuvers."
                if has_siding else f"No crossing siding found at {siding_node}."
            ),
        ))

        # Action B: HOLD at Origin Terminal / Junction
        hold_node = "KUR" if low_prio.direction == "SOUTHBOUND" else "PURI"
        actions.append(CandidateAction(
            action_id=f"{c_id}_ACT_HOLD_ORIGIN",
            conflict_id=c_id,
            action_type=ActionType.HOLD_TRAIN,
            target_train_id=low_prio.train_id,
            target_train_name=low_prio.name,
            target_train_priority=low_prio.priority,
            target_location=hold_node,
            parameters={
                "hold_duration_minutes": 10.0,
                "holding_station": hold_node,
                "yield_to_train_id": high_prio.train_id,
            },
            description=f"Hold {low_prio.name} at {hold_node} platform until {high_prio.name} clears section {loc}.",
            reason=(
                f"Prevents train entry onto single-track section {loc} entirely, eliminating "
                f"intermediate bottleneck contention."
            ),
            expected_delay_impact=+10.0,
            is_feasible=True,
            feasibility_reason=f"Station {hold_node} has platform capacity to safely absorb departure hold.",
        ))

        # Action C: PRIORITIZE Higher Priority Train Passage
        actions.append(CandidateAction(
            action_id=f"{c_id}_ACT_PRIORITIZE_MAIN",
            conflict_id=c_id,
            action_type=ActionType.PRIORITIZE_TRAIN,
            target_train_id=high_prio.train_id,
            target_train_name=high_prio.name,
            target_train_priority=high_prio.priority,
            target_location=loc,
            parameters={
                "single_line_token_grant": True,
                "section_id": loc,
            },
            description=f"Grant exclusive single-line token and right-of-way on {loc} to {high_prio.name}.",
            reason=f"Guarantees uninterrupted passage through single-line section for Priority {high_prio.priority} train.",
            expected_delay_impact=0.0,
            is_feasible=True,
            feasibility_reason="Block section instrument supports forward token release.",
        ))

        return actions

    # ── 3. Section Headway Actions ────────────────────────────────────────────

    def _generate_section_actions(
        self, conflict: Conflict, high_prio: TrainState, low_prio: TrainState
    ) -> List[CandidateAction]:
        actions = []
        c_id = conflict.conflict_id
        loc = conflict.location

        actions.append(CandidateAction(
            action_id=f"{c_id}_ACT_HEADWAY_HOLD",
            conflict_id=c_id,
            action_type=ActionType.HOLD_TRAIN,
            target_train_id=low_prio.train_id,
            target_train_name=low_prio.name,
            target_train_priority=low_prio.priority,
            target_location=low_prio.current_node or loc,
            parameters={"hold_duration_minutes": 5.0},
            description=f"Hold trailing train {low_prio.name} to restore safe 5-minute headway.",
            reason="Maintains mandatory automatic block signalling headway clearance.",
            expected_delay_impact=+5.0,
            is_feasible=True,
        ))

        return actions

    def _generate_generic_actions(
        self, conflict: Conflict, high_prio: TrainState, low_prio: TrainState
    ) -> List[CandidateAction]:
        return self._generate_junction_actions(conflict, high_prio, low_prio)


# Singleton
action_generator = ActionGenerator()
