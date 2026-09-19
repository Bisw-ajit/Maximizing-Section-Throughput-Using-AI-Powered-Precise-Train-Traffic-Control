"""
Unit and Integration Tests for RAIL-16:
Edge-Case Stress Testing & Siding Capacity Optimization
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.services.twin.digital_twin import digital_twin
from backend.services.optimization.siding_optimizer import siding_optimizer, StationSidingInfo
from backend.services.decision.action_generator import CandidateAction, ActionType
from backend.simulation.stress_runner import stress_test_runner, StressTestResult


class TestRail16SidingStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")
        cls.client = TestClient(app)

    def setUp(self):
        siding_optimizer.reset_occupancy()

    # ── 1. Scenario 003 Validation ────────────────────────────────────────────

    def test_scenario_003_stress_saturation_loading(self):
        """Verify scenario_003 loads with 10 trains, extreme delays, and TSRs."""
        scenario = scenario_loader.load("scenario_003", rail_network)
        self.assertEqual(scenario["scenario_id"], "scenario_003")
        self.assertEqual(len(scenario["trains"]), 10)
        self.assertEqual(scenario["difficulty"], "EXTREME")

        # Verify presence of Temporary Speed Restrictions
        tsrs = scenario.get("temporary_speed_restrictions", [])
        self.assertGreater(len(tsrs), 0)
        self.assertTrue(any(t["section_id"] == "KUR-SIL" for t in tsrs))

        # Verify timetable computation handles all 10 trains
        tt = scenario_loader.compute_timetable(scenario, rail_network)
        self.assertEqual(len(tt), 10)

    # ── 2. Siding Capacity & Headroom Calculations ────────────────────────────

    def test_station_siding_nominal_capacities(self):
        """Verify all junction and intermediate stations have configured loop capacities."""
        status_map = siding_optimizer.get_all_siding_status()
        self.assertIn("KUR", status_map)
        self.assertIn("BBS", status_map)
        self.assertIn("CTK", status_map)
        self.assertIn("PURI", status_map)
        self.assertIn("SIL", status_map)

        kur = status_map["KUR"]
        self.assertIsInstance(kur, StationSidingInfo)
        self.assertEqual(kur.total_capacity, 6)
        self.assertEqual(kur.available_headroom, 6)
        self.assertFalse(kur.is_saturated)

    def test_train_presence_and_utilization_tracking(self):
        """Verify adding and releasing trains updates headroom and utilization."""
        siding_optimizer.record_train_presence("KUR", "T001")
        siding_optimizer.record_train_presence("KUR", "T002")
        siding_optimizer.record_train_presence("KUR", "T003")

        st = siding_optimizer.get_station_status("KUR")
        self.assertEqual(st.occupied_count, 3)
        self.assertEqual(st.available_headroom, 3)
        self.assertAlmostEqual(st.utilization_pct, 50.0, delta=0.1)
        self.assertFalse(st.is_saturated)

        # Release one train
        siding_optimizer.release_train_presence("KUR", "T001")
        st_after = siding_optimizer.get_station_status("KUR")
        self.assertEqual(st_after.occupied_count, 2)
        self.assertEqual(st_after.available_headroom, 4)

    # ── 3. Secondary Deadlock Risk Detection ──────────────────────────────────

    def test_secondary_deadlock_detection(self):
        """Verify detector flags CRITICAL when holding additional trains exceeds loops."""
        # Sakhigopal has capacity 2
        siding_optimizer.record_train_presence("SIL", "T001")
        siding_optimizer.record_train_presence("SIL", "T002")

        st = siding_optimizer.get_station_status("SIL")
        self.assertTrue(st.is_saturated)
        self.assertEqual(st.available_headroom, 0)

        # Check holding another train at SIL
        risk = siding_optimizer.check_deadlock_risk("SIL", additional_holds=1)
        self.assertTrue(risk["has_risk"])
        self.assertEqual(risk["risk_level"], "CRITICAL")
        self.assertIn("DEADLOCK RISK", risk["reason"])

    # ── 4. Upstream Siding Reassignment & Optimization ────────────────────────

    def test_find_alternative_upstream_siding(self):
        """Verify finding nearest upstream siding with headroom along route."""
        # Fill KUR to saturation
        for i in range(1, 7):
            siding_optimizer.record_train_presence("KUR", f"T00{i}")

        # Southbound on route_A: CTK -> BGBR -> BBS -> RET -> KUR -> SIL -> PURI
        # Upstream of KUR is RET (if free)
        alt = siding_optimizer.find_alternative_upstream_siding("KUR", "route_A", "SOUTHBOUND")
        self.assertEqual(alt, "RET")

    def test_candidate_action_siding_optimization(self):
        """Verify candidate actions exceeding capacity are relocated or marked infeasible."""
        # Saturate SIL
        siding_optimizer.record_train_presence("SIL", "T001")
        siding_optimizer.record_train_presence("SIL", "T002")

        # Create candidate action to hold at SIL
        hold_act = CandidateAction(
            action_id="CONF_CROSS_SIL_HOLD",
            conflict_id="CONF_CROSS_01",
            action_type=ActionType.HOLD_TRAIN,
            target_train_id="T004",
            target_train_name="Santragachi-Puri Express",
            target_train_priority=3,
            target_location="SIL",
            parameters={"hold_duration_minutes": 8.0, "crossing_station": "SIL"},
            description="Hold at SIL loop for crossing",
            reason="Crossing clearance",
            expected_delay_impact=8.0,
            is_feasible=True,
        )

        optimized = siding_optimizer.optimize_candidate_actions([hold_act])
        self.assertEqual(len(optimized), 1)
        res_act = optimized[0]

        # Should either be relocated or marked infeasible
        if res_act.is_feasible:
            self.assertIn("RELOCATED", res_act.action_id)
        else:
            self.assertFalse(res_act.is_feasible)

    # ── 5. Stress Test Runner Simulation ──────────────────────────────────────

    def test_stress_test_runner_execution(self):
        """Verify stress_test_runner executes 10 trains and returns metrics."""
        result = stress_test_runner.run_stress_test(
            scenario_id="scenario_003",
            additional_delay_minutes=0.0,
            enforce_siding_limits=True,
        )

        self.assertIsInstance(result, StressTestResult)
        self.assertEqual(result.total_trains, 10)
        self.assertGreater(result.deadlocks_prevented, 0)
        self.assertGreater(result.resilience_score, 50.0)
        self.assertLess(result.recovery_time_ms, 250.0)
        self.assertGreater(len(result.station_siding_peaks), 0)
        self.assertIn("KUR", result.station_siding_peaks)

    # ── 6. REST API Endpoints ─────────────────────────────────────────────────

    def test_api_network_sidings_endpoint(self):
        """Verify GET /api/network/sidings returns 200 with all monitored stations."""
        with TestClient(app) as client:
            resp = client.get("/api/network/sidings")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            sidings = data["data"]["sidings"]
            self.assertIn("KUR", sidings)
            self.assertIn("BBS", sidings)
            self.assertEqual(sidings["KUR"]["total_capacity"], 6)

    def test_api_simulation_stress_test_endpoint(self):
        """Verify POST /api/simulation/stress-test returns 200 with full stress results."""
        with TestClient(app) as client:
            payload = {
                "scenario_id": "scenario_003",
                "additional_delay_minutes": 10.0,
                "enforce_siding_limits": True,
            }
            resp = client.post("/api/simulation/stress-test", json=payload)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            stress = data["data"]
            self.assertEqual(stress["total_trains"], 10)
            self.assertGreater(stress["deadlocks_prevented"], 0)
            self.assertIn("station_siding_peaks", stress)


if __name__ == "__main__":
    unittest.main()
