"""
Unit and Integration Tests for RAIL-17:
Baseline vs AI Performance Analytics Comparison Charts
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.simulation.dual_runner import dual_simulator
from backend.services.analytics.kpi_aggregator import kpi_aggregator


class TestRail17AnalyticsCompare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")
        cls.client = TestClient(app)

    def test_compare_endpoint_scenario_001(self):
        """Verify GET /api/analytics/compare for scenario_001 returns all metrics."""
        resp = self.client.get("/api/analytics/compare?scenario_id=scenario_001")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        comp = data["data"]

        self.assertEqual(comp["scenario_id"], "scenario_001")
        self.assertIn("baseline", comp)
        self.assertIn("ai_assisted", comp)
        self.assertIn("metrics_comparison", comp)
        self.assertIn("applied_ai_interventions", comp)

        metrics = comp["metrics_comparison"]
        self.assertGreaterEqual(metrics["delay_improvement_pct"], 0.0)
        self.assertIn("p1_delay_improvement_pct", metrics)
        self.assertGreaterEqual(metrics["waiting_time_reduction_pct"], 0.0)

        # Baseline vs AI per-train results
        base_trains = comp["baseline"]["train_results"]
        ai_trains = comp["ai_assisted"]["train_results"]
        self.assertEqual(len(base_trains), 5)
        self.assertEqual(len(ai_trains), 5)

    def test_compare_endpoint_stress_scenario_003(self):
        """Verify comparison executes on 10-train stress scenario."""
        resp = self.client.get("/api/analytics/compare?scenario_id=scenario_003")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        comp = data["data"]
        self.assertEqual(comp["scenario_id"], "scenario_003")
        self.assertEqual(comp["baseline"]["total_trains"], 10)
        self.assertEqual(comp["ai_assisted"]["total_trains"], 10)

    def test_summary_and_runs_endpoints(self):
        """Verify macro KPI summary and historical runs listing."""
        summary_resp = self.client.get("/api/analytics/summary")
        self.assertEqual(summary_resp.status_code, 200)
        summary_data = summary_resp.json()["data"]
        self.assertIn("total_runs", summary_data)
        self.assertIn("p1_protection_rate_pct", summary_data)
        self.assertIn("conflict_resolution_rate_pct", summary_data)

        runs_resp = self.client.get("/api/analytics/runs?limit=10")
        self.assertEqual(runs_resp.status_code, 200)
        runs_data = runs_resp.json()["data"]
        self.assertIn("runs", runs_data)
        self.assertIn("total", runs_data)


if __name__ == "__main__":
    unittest.main()
