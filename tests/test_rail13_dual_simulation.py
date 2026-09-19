"""
Unit and Integration Tests for RAIL-13:
Dual-Mode Simulation Engine (Baseline vs AI-Assisted)
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.services.twin.digital_twin import digital_twin
from backend.simulation.engine import simulation_engine, SimulationStrategy
from backend.simulation.dual_runner import dual_simulator


class TestRail13DualSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")
        cls.client = TestClient(app)

    def setUp(self):
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)
        digital_twin.load_scenario(scenario, timetable)
        simulation_engine.reset()

    # ── 1. Headless Fast-Forward Runner Tests ──────────────────────────────────

    def test_run_fast_forward_baseline(self):
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)

        res = dual_simulator.run_fast_forward(
            scenario=scenario,
            network=rail_network,
            timetable=timetable,
            strategy=SimulationStrategy.BASELINE,
        )

        self.assertEqual(res.strategy, "BASELINE")
        self.assertEqual(res.throughput, 5)
        self.assertGreater(len(res.train_results), 0)
        self.assertGreater(res.average_delay, 0.0)

    def test_run_fast_forward_ai_assisted(self):
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)

        res = dual_simulator.run_fast_forward(
            scenario=scenario,
            network=rail_network,
            timetable=timetable,
            strategy=SimulationStrategy.AI_ASSISTED,
        )

        self.assertEqual(res.strategy, "AI_ASSISTED")
        self.assertEqual(res.throughput, 5)
        self.assertGreater(len(res.train_results), 0)

    def test_compare_strategies_proves_ai_superiority(self):
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)

        comparison = dual_simulator.compare_strategies(scenario, rail_network, timetable)

        self.assertIn("baseline", comparison)
        self.assertIn("ai_assisted", comparison)
        self.assertIn("metrics_comparison", comparison)

        base = comparison["baseline"]
        ai = comparison["ai_assisted"]
        metrics = comparison["metrics_comparison"]

        # AI Assisted must produce lower or equal delay on Rajdhani (P1)
        self.assertLessEqual(ai["p1_delay"], base["p1_delay"])

        # Delay improvement percentage must be non-negative
        self.assertGreaterEqual(metrics["delay_improvement_pct"], 0.0)
        self.assertIn("summary", metrics)
        self.assertGreater(len(comparison["applied_ai_interventions"]), 0)

    # ── 2. Live Engine Strategy Switching ─────────────────────────────────────

    def test_engine_strategy_toggle(self):
        simulation_engine.set_strategy(SimulationStrategy.AI_ASSISTED)
        self.assertEqual(simulation_engine.strategy, SimulationStrategy.AI_ASSISTED)

        simulation_engine.set_strategy(SimulationStrategy.BASELINE)
        self.assertEqual(simulation_engine.strategy, SimulationStrategy.BASELINE)

    # ── 3. API Endpoints ──────────────────────────────────────────────────────

    def test_api_set_strategy(self):
        res = self.client.post("/api/simulation/strategy", json={"strategy": "AI_ASSISTED"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["strategy"], "AI_ASSISTED")

        # Invalid strategy
        res_bad = self.client.post("/api/simulation/strategy", json={"strategy": "INVALID"})
        self.assertEqual(res_bad.status_code, 400)

    def test_api_compare_simulation(self):
        res = self.client.post("/api/simulation/compare", json={"scenario_id": "scenario_001"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("baseline", data["data"])
        self.assertIn("ai_assisted", data["data"])

    def test_api_analytics_compare(self):
        res = self.client.get("/api/analytics/compare?scenario_id=scenario_001")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("metrics_comparison", data["data"])

    def test_api_analytics_runs(self):
        # Run compare first so cache exists
        self.client.get("/api/analytics/compare?scenario_id=scenario_001")
        res = self.client.get("/api/analytics/runs")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["data"]["total"], 2)


if __name__ == "__main__":
    unittest.main()
