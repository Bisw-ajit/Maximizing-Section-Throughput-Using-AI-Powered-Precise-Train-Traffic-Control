"""
RAILOPTIX — Multi-Objective Feasibility Evaluator & Decision Selector
=====================================================================
Evaluates candidate actions against multiple competing operational objectives:
  1. Priority Preservation (P1 Rajdhani/Vande Bharat > P2 > P3 > P4 > P5)
  2. Net Delay Minimization (cumulative corridor delay minutes)
  3. Wait-Time Minimization (idling at signals/sidings)
  4. Corridor Throughput Maximization
  5. Bottleneck / Congestion Relief

Fulfills: FR-05 & JIRA RAIL-10.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Optional, Any

from .action_generator import CandidateAction, ActionType
from ..twin.digital_twin import digital_twin, TrainState


class EvaluationProfile(str, Enum):
    BALANCED = "BALANCED"
    PRIORITY_FIRST = "PRIORITY_FIRST"
    THROUGHPUT_MAX = "THROUGHPUT_MAX"
    DELAY_MIN = "DELAY_MIN"


@dataclass
class ObjectiveWeights:
    priority_weight: float = 0.35
    delay_weight: float = 0.25
    wait_time_weight: float = 0.15
    throughput_weight: float = 0.15
    congestion_weight: float = 0.10

    def normalize(self) -> None:
        total = (
            self.priority_weight
            + self.delay_weight
            + self.wait_time_weight
            + self.throughput_weight
            + self.congestion_weight
        )
        if total > 0:
            self.priority_weight = round(self.priority_weight / total, 3)
            self.delay_weight = round(self.delay_weight / total, 3)
            self.wait_time_weight = round(self.wait_time_weight / total, 3)
            self.throughput_weight = round(self.throughput_weight / total, 3)
            self.congestion_weight = round(self.congestion_weight / total, 3)


PRESET_PROFILES: Dict[EvaluationProfile, ObjectiveWeights] = {
    EvaluationProfile.BALANCED: ObjectiveWeights(0.35, 0.25, 0.15, 0.15, 0.10),
    EvaluationProfile.PRIORITY_FIRST: ObjectiveWeights(0.55, 0.20, 0.10, 0.10, 0.05),
    EvaluationProfile.THROUGHPUT_MAX: ObjectiveWeights(0.15, 0.25, 0.15, 0.35, 0.10),
    EvaluationProfile.DELAY_MIN: ObjectiveWeights(0.20, 0.45, 0.20, 0.10, 0.05),
}


@dataclass
class EvaluatedAction:
    action: CandidateAction
    score: float                            # Overall Composite Utility Score (0.0 - 100.0)
    sub_scores: Dict[str, float]            # Individual objective scores
    expected_delay_change: float            # Net delta (+min extra delay / -min delay saved)
    expected_waiting_change: float          # Net delta in wait minutes
    feasible: bool
    trade_off_explanation: str
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.action.action_id,
            "conflict_id": self.action.conflict_id,
            "action_type": self.action.action_type.value,
            "target_train_id": self.action.target_train_id,
            "target_train_name": self.action.target_train_name,
            "target_train_priority": self.action.target_train_priority,
            "target_location": self.action.target_location,
            "parameters": self.action.parameters,
            "score": round(self.score, 2),
            "sub_scores": {k: round(v, 2) for k, v in self.sub_scores.items()},
            "reason": self.action.reason,
            "description": self.action.description,
            "trade_off_explanation": self.trade_off_explanation,
            "expected_delay_change": round(self.expected_delay_change, 2),
            "expected_waiting_change": round(self.expected_waiting_change, 2),
            "feasible": self.feasible,
            "feasibility_reason": self.action.feasibility_reason,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class MultiObjectiveEvaluator:
    """
    Computes Pareto-weighted multi-attribute utility scores for all candidate actions.
    """

    def __init__(self, default_weights: Optional[ObjectiveWeights] = None):
        self.weights = default_weights or ObjectiveWeights()
        self.weights.normalize()

    def set_weights(self, weights: ObjectiveWeights) -> None:
        weights.normalize()
        self.weights = weights

    def set_profile(self, profile: EvaluationProfile) -> None:
        if profile in PRESET_PROFILES:
            self.set_weights(PRESET_PROFILES[profile])

    def evaluate_candidates(
        self,
        candidates: List[CandidateAction],
        weights: Optional[ObjectiveWeights] = None,
    ) -> List[EvaluatedAction]:
        """Evaluate and rank all candidate actions by composite utility score."""
        w = weights or self.weights
        w.normalize()

        evaluated: List[EvaluatedAction] = []
        for cand in candidates:
            ev = self._evaluate_single_action(cand, w)
            evaluated.append(ev)

        # Sort descending: Feasible first, then highest score
        evaluated.sort(key=lambda e: (1 if e.feasible else 0, e.score), reverse=True)
        return evaluated

    def select_best(
        self,
        candidates: List[CandidateAction],
        weights: Optional[ObjectiveWeights] = None,
    ) -> Optional[EvaluatedAction]:
        """Select the highest-scoring feasible candidate action."""
        ranked = self.evaluate_candidates(candidates, weights)
        feasible_ranked = [e for e in ranked if e.feasible]
        return feasible_ranked[0] if feasible_ranked else (ranked[0] if ranked else None)

    # ── Internal Evaluation Mechanics ────────────────────────────────────────

    def _evaluate_single_action(self, action: CandidateAction, w: ObjectiveWeights) -> EvaluatedAction:
        if not action.is_feasible:
            return EvaluatedAction(
                action=action,
                score=0.0,
                sub_scores={"priority": 0.0, "delay": 0.0, "wait_time": 0.0, "throughput": 0.0, "congestion": 0.0},
                expected_delay_change=action.expected_delay_impact,
                expected_waiting_change=action.expected_delay_impact,
                feasible=False,
                trade_off_explanation=f"Infeasible action rejected: {action.feasibility_reason}",
            )

        # 1. Priority Score (0 - 100)
        prio_score = self._score_priority(action)

        # 2. Delay Score (0 - 100)
        delay_score = self._score_delay(action)

        # 3. Wait-Time Score (0 - 100)
        wait_score = self._score_wait_time(action)

        # 4. Throughput Score (0 - 100)
        thr_score = self._score_throughput(action)

        # 5. Congestion Relief Score (0 - 100)
        cong_score = self._score_congestion_relief(action)

        # Weighted Composite Utility Score
        composite_score = (
            w.priority_weight * prio_score
            + w.delay_weight * delay_score
            + w.wait_time_weight * wait_score
            + w.throughput_weight * thr_score
            + w.congestion_weight * cong_score
        )
        composite_score = max(0.0, min(100.0, composite_score))

        # Waiting time impact estimation
        wait_impact = 0.0
        if action.action_type in (ActionType.HOLD_TRAIN, ActionType.CROSSING_WAIT):
            wait_impact = float(action.parameters.get("hold_duration_minutes", 6.0))
        elif action.action_type == ActionType.SPEED_ADVISORY:
            wait_impact = 0.0  # rolling deceleration, no idle wait

        trade_off_text = self._build_trade_off_narrative(
            action, composite_score, prio_score, delay_score, wait_impact
        )

        return EvaluatedAction(
            action=action,
            score=composite_score,
            sub_scores={
                "priority": prio_score,
                "delay": delay_score,
                "wait_time": wait_score,
                "throughput": thr_score,
                "congestion": cong_score,
            },
            expected_delay_change=action.expected_delay_impact,
            expected_waiting_change=wait_impact,
            feasible=True,
            trade_off_explanation=trade_off_text,
        )

    def _score_priority(self, action: CandidateAction) -> float:
        """Evaluates compliance with Indian Railways train precedence rules."""
        train_prio = action.target_train_priority

        if action.action_type == ActionType.PRIORITIZE_TRAIN:
            # Granting priority to P1 is best (100), P2 is 85, etc.
            return max(50.0, 100.0 - (train_prio - 1) * 15.0)

        elif action.action_type in (ActionType.HOLD_TRAIN, ActionType.CROSSING_WAIT):
            # Holding a lower-priority train (P3, P4, P5) scores much higher than holding a P1
            if train_prio == 1:
                return 15.0  # Penalize holding Rajdhani/Vande Bharat
            elif train_prio == 2:
                return 75.0  # Acceptable if yielding to P1
            elif train_prio >= 3:
                return 95.0  # Standard practice: express/freight yields to superior train

        elif action.action_type == ActionType.SPEED_ADVISORY:
            return 88.0

        return 70.0

    def _score_delay(self, action: CandidateAction) -> float:
        """Rewards minimum added delay or delay reduction."""
        extra_delay = action.expected_delay_impact
        if extra_delay <= 0.0:
            return 100.0
        # Decay: 5 min extra -> 75, 10 min extra -> 50, 15 min extra -> 25
        return max(10.0, 100.0 - (extra_delay * 5.0))

    def _score_wait_time(self, action: CandidateAction) -> float:
        """Penalizes idle stationary waiting at signals or loops."""
        if action.action_type == ActionType.SPEED_ADVISORY:
            return 95.0  # No idle stop, trains keep moving
        if action.action_type == ActionType.PRIORITIZE_TRAIN:
            return 100.0  # Zero wait time for prioritized train

        hold_min = float(action.parameters.get("hold_duration_minutes", 6.0))
        return max(15.0, 100.0 - (hold_min * 6.0))

    def _score_throughput(self, action: CandidateAction) -> float:
        """Evaluates effect on overall corridor train flow."""
        if action.action_type == ActionType.PRIORITIZE_TRAIN:
            return 95.0
        if action.action_type == ActionType.SPEED_ADVISORY:
            return 90.0
        if action.action_type == ActionType.CROSSING_WAIT:
            return 82.0  # Keeps both trains moving through section with scheduled crossing
        return 70.0

    def _score_congestion_relief(self, action: CandidateAction) -> float:
        """Rewards maneuvers that clear single-line tracks and junction diamonds."""
        if action.action_type == ActionType.CROSSING_WAIT:
            return 95.0  # Utilizing loop siding specifically clears single track
        if action.action_type == ActionType.PRIORITIZE_TRAIN:
            return 90.0
        if action.action_type == ActionType.SPEED_ADVISORY:
            return 85.0
        return 75.0

    def _build_trade_off_narrative(
        self, action: CandidateAction, score: float, prio: float, delay: float, wait: float
    ) -> str:
        """Generate plain-English explanation of the multi-objective trade-offs."""
        if action.action_type == ActionType.PRIORITIZE_TRAIN:
            return (
                f"Optimal priority enforcement ({score:.1f}/100): Grants zero-delay green corridor to "
                f"{action.target_train_name} (P{action.target_train_priority}), maximizing corridor throughput."
            )
        elif action.action_type == ActionType.SPEED_ADVISORY:
            return (
                f"Energy-efficient headway regulation ({score:.1f}/100): Eliminates {wait:.1f}m idle stop "
                f"via minor speed regulation, incurring only +{action.expected_delay_impact:.1f}m rolling delta."
            )
        elif action.action_type == ActionType.CROSSING_WAIT:
            stn = action.parameters.get("crossing_station", "siding")
            return (
                f"Single-line crossing optimization ({score:.1f}/100): Diverts {action.target_train_name} "
                f"into {stn} loop line for {wait:.1f}m, resolving opposing standoff while preserving mainline clearance."
            )
        else:
            return (
                f"Precedence hold ({score:.1f}/100): Incurs +{action.expected_delay_impact:.1f}m delay on "
                f"{action.target_train_name} to guarantee collision-free junction passage for superior service."
            )


# Singleton
multi_objective_evaluator = MultiObjectiveEvaluator()
