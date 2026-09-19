"""
Unit and Integration Tests for RAIL-10:
Multi-Objective Feasibility Evaluator & Decision Selector
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.services.twin.digital_twin import digital_twin
from backend.services.decision.evaluator import (
    multi_objective_evaluator,
    ObjectiveWeights,
    EvaluationProfile,
)
from backend.services.decision.action_generator import (
    action_generator,
    CandidateAction,
    ActionType,
)
from backend.services.decision.engine import decision_engine


class TestRail10DecisionSelector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")
        cls.client = TestClient(app)

    def setUp(self):
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)
        digital_twin.load_scenario(scenario, timetable)
        decision_engine.clear_history()

    # ── 1. Multi-Objective Scoring Mechanics ──────────────────────────────────

    def test_composite_scoring_and_sub_scores(self):
        action = CandidateAction(
            action_id="TEST_ACT_01",
            conflict_id="CONF_001",
            action_type=ActionType.HOLD_TRAIN,
            target_train_id="T001",
            target_train_name="Puri Express",
            target_train_priority=2,
            target_location="CTK",
            parameters={"hold_duration_minutes": 5.0},
            description="Hold test action",
            reason="Priority clearance",
            expected_delay_impact=+5.0,
            is_feasible=True,
        )

        evaluated = multi_objective_evaluator.evaluate_candidates([action])
        self.assertEqual(len(evaluated), 1)
        ev = evaluated[0]

        # Score must be bounded between 0 and 100
        self.assertGreater(ev.score, 0.0)
        self.assertLessEqual(ev.score, 100.0)

        # Verify all sub-score components present
        sub = ev.sub_scores
        self.assertIn("priority", sub)
        self.assertIn("delay", sub)
        self.assertIn("wait_time", sub)
        self.assertIn("throughput", sub)
        self.assertIn("congestion", sub)

        # Trade-off text generated
        self.assertTrue(len(ev.trade_off_explanation) > 10)

    def test_infeasible_action_rejected_score_zero(self):
        infeasible_action = CandidateAction(
            action_id="TEST_ACT_INFEASIBLE",
            conflict_id="CONF_001",
            action_type=ActionType.REROUTE,
            target_train_id="T001",
            target_train_name="Puri Express",
            target_train_priority=2,
            target_location="KUR",
            parameters={},
            description="Infeasible detour",
            reason="Detour check",
            expected_delay_impact=20.0,
            is_feasible=False,
            feasibility_reason="No bypass corridor available",
        )

        evaluated = multi_objective_evaluator.evaluate_candidates([infeasible_action])
        self.assertEqual(len(evaluated), 1)
        self.assertEqual(evaluated[0].score, 0.0)
        self.assertFalse(evaluated[0].feasible)

    # ── 2. Decision Engine End-to-End Evaluation ──────────────────────────────

    def test_decision_engine_evaluation(self):
        res = decision_engine.evaluate_and_recommend(profile="BALANCED")
        self.assertGreater(res["total_candidates"], 0)
        self.assertGreater(res["feasible_count"], 0)
        self.assertIsNotNone(res["recommended"])

        rec = res["recommended"]
        self.assertTrue(rec["feasible"])
        self.assertGreater(rec["score"], 0.0)

    def test_profile_weight_adaptation(self):
        res_prio = decision_engine.evaluate_and_recommend(profile="PRIORITY_FIRST")
        self.assertEqual(res_prio["active_weights"]["priority"], 0.55)

        res_delay = decision_engine.evaluate_and_recommend(profile="DELAY_MIN")
        self.assertEqual(res_delay["active_weights"]["delay"], 0.45)

    # ── 3. Action Execution & Digital Twin State Update ───────────────────────

    def test_apply_recommendation_updates_twin(self):
        res = decision_engine.evaluate_and_recommend()
        candidates = res["candidates"]
        hold_action = next((c for c in candidates if c["action_type"] == "HOLD_TRAIN" and c["feasible"]), None)
        self.assertIsNotNone(hold_action)

        target_train_id = hold_action["target_train_id"]
        train_before = digital_twin.get_train(target_train_id)
        delay_before = train_before.delay_minutes

        # Apply action
        apply_res = decision_engine.apply_action(hold_action["recommendation_id"])
        self.assertTrue(apply_res["success"])

        # Verify train state in Digital Twin
        train_after = digital_twin.get_train(target_train_id)
        self.assertEqual(train_after.status, "HELD")
        self.assertGreater(train_after.delay_minutes, delay_before)

        # Verify audit history
        history = decision_engine.get_applied_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action_id"], hold_action["recommendation_id"])

    # ── 4. API Endpoints for Recommendations ──────────────────────────────────

    def test_api_post_recommendations_custom_weights(self):
        payload = {
            "profile": "THROUGHPUT_MAX",
            "weights": {"priority": 0.2, "delay": 0.2, "wait_time": 0.2, "throughput": 0.3, "congestion": 0.1}
        }
        res = self.client.post("/api/recommendations", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["data"]["recommended"])

    def test_api_profiles_endpoint(self):
        res = self.client.get("/api/recommendations/profiles")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("BALANCED", data["data"]["profiles"])
        self.assertIn("PRIORITY_FIRST", data["data"]["profiles"])

    def test_api_apply_and_history_lifecycle(self):
        # 1. Fetch recommendations
        rec_res = self.client.post("/api/recommendations")
        rec_data = rec_res.json()["data"]
        action_id = rec_data["recommended"]["recommendation_id"]

        # 2. Apply the recommended action
        apply_res = self.client.post("/api/recommendations/apply", json={"action_id": action_id})
        self.assertEqual(apply_res.status_code, 200)
        self.assertTrue(apply_res.json()["success"])

        # 3. Verify audit history
        hist_res = self.client.get("/api/recommendations/history")
        self.assertEqual(hist_res.status_code, 200)
        hist_data = hist_res.json()["data"]
        self.assertGreaterEqual(hist_data["total_applied"], 1)
        self.assertEqual(hist_data["history"][-1]["action_id"], action_id)


if __name__ == "__main__":
    unittest.main()
