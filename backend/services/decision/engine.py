"""
RAILOPTIX — Autonomous AI Decision Engine
==========================================
Coordinates:
  1. Automated Conflict Identification
  2. Candidate Action Synthesis (RAIL-9)
  3. Multi-Objective Feasibility Evaluation & Scoring (RAIL-10)
  4. Real-Time Intervention Execution & Audit Logging (Digital Twin & Simulation)

Fulfills: JIRA RAIL-10 & Foundation for RAIL-11.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from threading import Lock

from ..conflict.conflict_detector import conflict_detector, Conflict
from .action_generator import action_generator, CandidateAction, ActionType
from .evaluator import (
    multi_objective_evaluator,
    EvaluatedAction,
    ObjectiveWeights,
    EvaluationProfile,
    PRESET_PROFILES,
)
from ..twin.digital_twin import digital_twin

logger = logging.getLogger("railoptix.decision.engine")


class DecisionEngine:
    """
    Central AI dispatch reasoning and action execution engine.
    """

    def __init__(self):
        self._lock = Lock()
        self._applied_history: List[Dict[str, Any]] = []

    def evaluate_and_recommend(
        self,
        conflict_id: Optional[str] = None,
        profile: Optional[str] = None,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Run end-to-end evaluation pipeline:
        detect conflicts -> generate candidate actions -> multi-objective score -> select recommended.
        """
        # Resolve weights
        weights = None
        if custom_weights:
            weights = ObjectiveWeights(
                priority_weight=custom_weights.get("priority", 0.35),
                delay_weight=custom_weights.get("delay", 0.25),
                wait_time_weight=custom_weights.get("wait_time", 0.15),
                throughput_weight=custom_weights.get("throughput", 0.15),
                congestion_weight=custom_weights.get("congestion", 0.10),
            )
        elif profile:
            prof_enum = EvaluationProfile(profile.upper())
            weights = PRESET_PROFILES.get(prof_enum)

        # 1. Detect conflicts
        all_conflicts = conflict_detector.detect_all()
        if not all_conflicts:
            return {
                "candidates": [],
                "recommended": None,
                "total_candidates": 0,
                "feasible_count": 0,
                "conflicts_count": 0,
                "message": "No active conflicts detected on the corridor.",
            }

        target_conflicts = all_conflicts
        if conflict_id:
            target_conflicts = [c for c in all_conflicts if c.conflict_id == conflict_id]
            if not target_conflicts:
                raise ValueError(f"Conflict '{conflict_id}' not found.")

        # 2. Generate candidate actions
        all_candidates: List[CandidateAction] = []
        for conf in target_conflicts:
            cands = action_generator.generate_actions_for_conflict(conf)
            all_candidates.extend(cands)

        # 3. Multi-objective evaluation & ranking
        evaluated = multi_objective_evaluator.evaluate_candidates(all_candidates, weights)
        best = multi_objective_evaluator.select_best(all_candidates, weights)

        return {
            "candidates": [e.to_dict() for e in evaluated],
            "recommended": best.to_dict() if best else None,
            "total_candidates": len(evaluated),
            "feasible_count": sum(1 for e in evaluated if e.feasible),
            "conflicts_count": len(target_conflicts),
            "active_weights": {
                "priority": (weights or multi_objective_evaluator.weights).priority_weight,
                "delay": (weights or multi_objective_evaluator.weights).delay_weight,
                "wait_time": (weights or multi_objective_evaluator.weights).wait_time_weight,
                "throughput": (weights or multi_objective_evaluator.weights).throughput_weight,
                "congestion": (weights or multi_objective_evaluator.weights).congestion_weight,
            },
        }

    def apply_action(self, action_id: str) -> Dict[str, Any]:
        """
        Execute an evaluated decision action by applying it to the Digital Twin.
        Updates train statuses, records delay delta, and saves into audit log.
        """
        # Re-evaluate all conflicts to find the candidate action
        all_conflicts = conflict_detector.detect_all()
        target_action: Optional[CandidateAction] = None

        for conf in all_conflicts:
            cands = action_generator.generate_actions_for_conflict(conf)
            for c in cands:
                if c.action_id == action_id:
                    target_action = c
                    break
            if target_action:
                break

        if not target_action:
            raise ValueError(f"Candidate action '{action_id}' not found.")

        if not target_action.is_feasible:
            raise ValueError(f"Cannot apply infeasible action: {target_action.feasibility_reason}")

        now = datetime.now(timezone.utc)
        tid = target_action.target_train_id
        train = digital_twin.get_train(tid)

        # Apply state changes to Digital Twin
        applied_details: Dict[str, Any] = {
            "action_id": target_action.action_id,
            "action_type": target_action.action_type.value,
            "target_train_id": tid,
            "target_train_name": target_action.target_train_name,
            "location": target_action.target_location,
            "applied_at": now.isoformat(),
            "status": "APPLIED",
        }

        if train:
            if target_action.action_type == ActionType.HOLD_TRAIN:
                hold_min = float(target_action.parameters.get("hold_duration_minutes", 5.0))
                digital_twin.update_train_state(
                    tid,
                    status="HELD",
                    delay_minutes=train.delay_minutes + hold_min,
                )
                applied_details["new_status"] = "HELD"
                applied_details["added_delay_minutes"] = hold_min

            elif target_action.action_type == ActionType.CROSSING_WAIT:
                siding = target_action.parameters.get("crossing_station", target_action.target_location)
                hold_min = float(target_action.parameters.get("hold_duration_minutes", 8.0))
                digital_twin.update_train_state(
                    tid,
                    status="HELD",
                    current_node=siding,
                    current_section=None,
                    delay_minutes=train.delay_minutes + hold_min,
                )
                applied_details["new_status"] = "HELD"
                applied_details["siding_station"] = siding

            elif target_action.action_type == ActionType.PRIORITIZE_TRAIN:
                digital_twin.update_train_state(
                    tid,
                    status="EN_ROUTE",
                )
                applied_details["new_status"] = "PRIORITIZED"

            elif target_action.action_type == ActionType.SPEED_ADVISORY:
                target_speed = target_action.parameters.get("target_speed_kmh", 60.0)
                applied_details["advisory_speed_kmh"] = target_speed

        with self._lock:
            self._applied_history.append(applied_details)

        logger.info("Decision action %s applied to train %s successfully.", action_id, tid)
        return {
            "success": True,
            "applied_action": applied_details,
            "message": f"Action '{action_id}' successfully executed on Digital Twin.",
        }

    def get_applied_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._applied_history)

    def clear_history(self) -> None:
        with self._lock:
            self._applied_history.clear()


# Singleton
decision_engine = DecisionEngine()
