"""
Unit and Integration Tests for RAIL-9:
Candidate Action Generator for Junction Bottlenecks & Single-Line Contention
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.services.twin.digital_twin import digital_twin
from backend.services.conflict.conflict_detector import (
    conflict_detector,
    ConflictType,
    ConflictSeverity,
)
from backend.services.decision.action_generator import (
    action_generator,
    ActionType,
)


class TestRail9ActionGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")
        cls.client = TestClient(app)

    def setUp(self):
        # Load scenario_001 which contains Khurda Road junction and single-line crossing conflicts
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)
        digital_twin.load_scenario(scenario, timetable)

    # ── 1. Conflict Detection Verification ────────────────────────────────────

    def test_detect_scenario_conflicts(self):
        conflicts = conflict_detector.detect_all()
        self.assertGreaterEqual(len(conflicts), 2)

        types = [c.conflict_type for c in conflicts]
        self.assertIn(ConflictType.JUNCTION_CONFLICT, types)
        self.assertIn(ConflictType.CROSSING_CONFLICT, types)

        # Check Khurda Road junction conflict
        kur_conflict = next((c for c in conflicts if c.location == "KUR"), None)
        self.assertIsNotNone(kur_conflict)
        self.assertIn("T001", kur_conflict.train_ids)
        self.assertIn("T003", kur_conflict.train_ids)

    # ── 2. Candidate Action Generation for Junction Bottleneck ────────────────

    def test_junction_candidate_actions(self):
        conflicts = conflict_detector.detect_all()
        kur_conflict = next((c for c in conflicts if c.location == "KUR"), None)
        self.assertIsNotNone(kur_conflict)

        candidates = action_generator.generate_actions_for_conflict(kur_conflict)
        self.assertGreaterEqual(len(candidates), 3)

        action_types = [a.action_type for a in candidates]
        self.assertIn(ActionType.HOLD_TRAIN, action_types)
        self.assertIn(ActionType.PRIORITIZE_TRAIN, action_types)
        self.assertIn(ActionType.SPEED_ADVISORY, action_types)

        # Verify that lower-priority train (T001, P2) is targeted for HOLD
        hold_action = next((a for a in candidates if a.action_type == ActionType.HOLD_TRAIN), None)
        self.assertIsNotNone(hold_action)
        self.assertEqual(hold_action.target_train_id, "T001")
        self.assertTrue(hold_action.is_feasible)
        self.assertGreater(hold_action.expected_delay_impact, 0)

        # Verify that higher-priority train (T003, P1 Rajdhani) is targeted for PRIORITIZE
        prio_action = next((a for a in candidates if a.action_type == ActionType.PRIORITIZE_TRAIN), None)
        self.assertIsNotNone(prio_action)
        self.assertEqual(prio_action.target_train_id, "T003")
        self.assertTrue(prio_action.is_feasible)

        # Verify SPEED_ADVISORY exists
        speed_action = next((a for a in candidates if a.action_type == ActionType.SPEED_ADVISORY), None)
        self.assertIsNotNone(speed_action)
        self.assertIn("speed_delta_kmh", speed_action.parameters)

    # ── 3. Candidate Action Generation for Single-Line Crossing ───────────────

    def test_crossing_candidate_actions(self):
        conflicts = conflict_detector.detect_all()
        crossing_conflict = next((c for c in conflicts if c.conflict_type == ConflictType.CROSSING_CONFLICT), None)
        self.assertIsNotNone(crossing_conflict)

        candidates = action_generator.generate_actions_for_conflict(crossing_conflict)
        self.assertGreaterEqual(len(candidates), 2)

        action_types = [a.action_type for a in candidates]
        self.assertIn(ActionType.CROSSING_WAIT, action_types)

        # Verify crossing siding assignment (Sakhigopal SIL)
        cross_action = next((a for a in candidates if a.action_type == ActionType.CROSSING_WAIT), None)
        self.assertIsNotNone(cross_action)
        self.assertEqual(cross_action.parameters.get("crossing_station"), "SIL")
        self.assertTrue(cross_action.is_feasible)

    # ── 4. API Endpoints for Conflicts & Candidates ───────────────────────────

    def test_api_get_conflicts(self):
        res = self.client.get("/api/conflicts")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["data"]["total"], 2)

    def test_api_get_conflict_candidates(self):
        # Fetch conflicts first
        res = self.client.get("/api/conflicts")
        conflicts = res.json()["data"]["conflicts"]
        first_id = conflicts[0]["conflict_id"]

        # Request candidate actions
        res = self.client.get(f"/api/conflicts/{first_id}/candidates")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreater(data["data"]["total_candidates"], 0)
        self.assertGreater(data["data"]["feasible_count"], 0)

    def test_api_recommendations(self):
        res = self.client.post("/api/recommendations")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreater(data["data"]["total_candidates"], 0)
        self.assertIsNotNone(data["data"]["recommended"])


if __name__ == "__main__":
    unittest.main()
