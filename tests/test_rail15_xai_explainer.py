"""
Unit and Integration Tests for RAIL-15:
Explainable AI (XAI) Natural Language Decision Reasoner
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.services.twin.digital_twin import digital_twin
from backend.services.decision.action_generator import CandidateAction, ActionType
from backend.services.decision.evaluator import multi_objective_evaluator
from backend.services.decision.explainer import (
    xai_explainer,
    DecisionExplanation,
    FactorAttribution,
    CounterfactualCase,
    RegulatoryCompliance,
)
from backend.services.decision.engine import decision_engine


class TestRail15XAIExplainer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")
        cls.client = TestClient(app)

    def setUp(self):
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)
        digital_twin.load_scenario(scenario, timetable)
        decision_engine.clear_history()

    def test_explainer_generates_complete_explanation(self):
        """Verify XAI explainer generates all 4 audit tiers for a recommended action."""
        action_primary = CandidateAction(
            action_id="CONF_001_ACT_PRIO_HIGH",
            conflict_id="CONF_001",
            action_type=ActionType.PRIORITIZE_TRAIN,
            target_train_id="T003",
            target_train_name="New Delhi Rajdhani Express",
            target_train_priority=1,
            target_location="KUR",
            parameters={},
            description="Grant priority transit to T003 New Delhi Rajdhani Express",
            reason="P1 train precedence",
            expected_delay_impact=0.0,
            is_feasible=True,
        )

        action_alt = CandidateAction(
            action_id="CONF_001_ACT_HOLD_LOW",
            conflict_id="CONF_001",
            action_type=ActionType.HOLD_TRAIN,
            target_train_id="T001",
            target_train_name="Puri Express",
            target_train_priority=2,
            target_location="KUR",
            parameters={"hold_duration_minutes": 6.0},
            description="Hold T001 Puri Express at KUR",
            reason="Regulate lower priority service",
            expected_delay_impact=6.0,
            is_feasible=True,
        )

        evaluated = multi_objective_evaluator.evaluate_candidates([action_primary, action_alt])
        explanation = xai_explainer.explain_action(evaluated[0], alternatives=evaluated[1:])

        self.assertIsInstance(explanation, DecisionExplanation)
        self.assertEqual(explanation.recommendation_id, "CONF_001_ACT_PRIO_HIGH")
        self.assertEqual(explanation.conflict_id, "CONF_001")
        self.assertEqual(explanation.target_train_name, "New Delhi Rajdhani Express")
        self.assertIn("Grant continuous green aspect", explanation.executive_summary)

        # Factor Attributions
        self.assertGreater(len(explanation.key_drivers), 0)
        total_pct = sum(d.impact_pct for d in explanation.key_drivers)
        self.assertAlmostEqual(total_pct, 100.0, delta=1.0)

        # Counterfactuals
        self.assertGreater(len(explanation.counterfactuals), 0)
        self.assertIn("HOLD_TRAIN", explanation.counterfactuals[0].alternative_type)

        # Regulatory Compliance
        self.assertGreater(len(explanation.regulatory_compliance), 0)
        rule_codes = [r.rule_code for r in explanation.regulatory_compliance]
        self.assertTrue(any("G&SR" in rc or "SWR" in rc for rc in rule_codes))

    def test_explainer_action_types_executive_summaries(self):
        """Verify distinct executive summaries for different action types."""
        hold_action = CandidateAction(
            action_id="ACT_HOLD",
            conflict_id="CONF_002",
            action_type=ActionType.HOLD_TRAIN,
            target_train_id="T002",
            target_train_name="Dhauli Express",
            target_train_priority=2,
            target_location="BBS",
            parameters={"hold_duration_minutes": 4.5},
            description="Hold test",
            reason="Deconflict",
            expected_delay_impact=4.5,
            is_feasible=True,
        )
        cross_action = CandidateAction(
            action_id="ACT_CROSS",
            conflict_id="CONF_002",
            action_type=ActionType.CROSSING_WAIT,
            target_train_id="T002",
            target_train_name="Dhauli Express",
            target_train_priority=2,
            target_location="KUR",
            parameters={"crossing_station": "KUR", "hold_duration_minutes": 7.0},
            description="Crossing test",
            reason="Single line crossing",
            expected_delay_impact=7.0,
            is_feasible=True,
        )
        speed_action = CandidateAction(
            action_id="ACT_SPEED",
            conflict_id="CONF_002",
            action_type=ActionType.SPEED_ADVISORY,
            target_train_id="T002",
            target_train_name="Dhauli Express",
            target_train_priority=2,
            target_location="BBS",
            parameters={"speed_delta_kmh": -15.0},
            description="Speed advisory test",
            reason="Approach spacing",
            expected_delay_impact=2.0,
            is_feasible=True,
        )

        ev_hold = multi_objective_evaluator.evaluate_candidates([hold_action])[0]
        ev_cross = multi_objective_evaluator.evaluate_candidates([cross_action])[0]
        ev_speed = multi_objective_evaluator.evaluate_candidates([speed_action])[0]

        expl_hold = xai_explainer.explain_action(ev_hold)
        expl_cross = xai_explainer.explain_action(ev_cross)
        expl_speed = xai_explainer.explain_action(ev_speed)

        self.assertIn("Hold", expl_hold.executive_summary)
        self.assertIn("Divert", expl_cross.executive_summary)
        self.assertIn("speed reduction advisory", expl_speed.executive_summary)

    def test_api_recommendation_explain_endpoint(self):
        """Verify GET /api/recommendations/{recommendation_id}/explain returns 200 with XAI data."""
        # 1. Trigger recommendations
        post_resp = self.client.post("/api/recommendations", json={"profile": "BALANCED"})
        self.assertEqual(post_resp.status_code, 200)
        resp_data = post_resp.json()
        self.assertTrue(resp_data["success"])
        rec_data = resp_data["data"]
        recommended = rec_data.get("recommended")
        self.assertIsNotNone(recommended)

        first_rec_id = recommended["recommendation_id"]

        # 2. Call explain endpoint
        explain_resp = self.client.get(f"/api/recommendations/{first_rec_id}/explain")
        self.assertEqual(explain_resp.status_code, 200)

        data = explain_resp.json()
        self.assertTrue(data["success"])
        explanation = data["data"]
        self.assertEqual(explanation["recommendation_id"], first_rec_id)
        self.assertIn("executive_summary", explanation)
        self.assertIn("key_drivers", explanation)
        self.assertIn("counterfactuals", explanation)
        self.assertIn("regulatory_compliance", explanation)
        self.assertIn("model_attribution", explanation)
        self.assertGreater(len(explanation["key_drivers"]), 0)

    def test_api_recommendation_explain_not_found(self):
        """Verify GET /api/recommendations/INVALID_ID/explain returns 404."""
        resp = self.client.get("/api/recommendations/NON_EXISTENT_REC_ID/explain")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("detail", resp.json())


if __name__ == "__main__":
    unittest.main()
