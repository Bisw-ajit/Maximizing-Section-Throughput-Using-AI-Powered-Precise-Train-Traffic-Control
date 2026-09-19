"""
Unit and Integration Tests for RAIL-14:
Historical Simulation Database Service & KPI Aggregator
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.services.analytics.kpi_aggregator import kpi_aggregator
from backend.simulation.dual_runner import dual_simulator


class TestRail14KPIAggregator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")
        cls.client = TestClient(app)

    def setUp(self):
        kpi_aggregator.clear_cache()

    # ── 1. KPI Aggregator Service Direct Tests ────────────────────────────────

    def test_save_and_retrieve_runs(self):
        # Save baseline run
        b_data = {
            "run_id": "TEST_BASE_001",
            "scenario_id": "scenario_001",
            "strategy": "BASELINE",
            "throughput": 5,
            "average_delay": 15.0,
            "p1_delay": 18.0,
            "waiting_time": 40.0,
            "conflict_count": 3,
            "utilization": 1.0,
        }
        import asyncio
        asyncio.run(kpi_aggregator.save_run(b_data))

        # Save AI run
        ai_data = {
            "run_id": "TEST_AI_001",
            "scenario_id": "scenario_001",
            "strategy": "AI_ASSISTED",
            "throughput": 5,
            "average_delay": 4.0,
            "p1_delay": 0.0,
            "waiting_time": 10.0,
            "conflict_count": 0,
            "utilization": 1.0,
        }
        asyncio.run(kpi_aggregator.save_run(ai_data))

        runs = asyncio.run(kpi_aggregator.get_runs(limit=10))
        self.assertGreaterEqual(len(runs), 2)

        summary = kpi_aggregator.get_summary("scenario_001")
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["baseline_count"], 1)
        self.assertEqual(summary["ai_count"], 1)
        self.assertGreater(summary["total_delay_minutes_saved"], 0.0)
        self.assertGreater(summary["avg_delay_reduction_pct"], 50.0)
        self.assertEqual(summary["p1_protection_rate_pct"], 100.0)
        self.assertEqual(summary["conflict_resolution_rate_pct"], 100.0)
        self.assertEqual(len(summary["recent_trends"]), 2)

    # ── 2. Automatic Persistence via Dual Simulation ─────────────────────────

    def test_dual_simulation_auto_persists(self):
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)

        # Running comparison should automatically persist both runs
        dual_simulator.compare_strategies(scenario, rail_network, timetable)

        summary = kpi_aggregator.get_summary("scenario_001")
        self.assertGreaterEqual(summary["total_runs"], 2)
        self.assertGreaterEqual(summary["ai_count"], 1)
        self.assertGreaterEqual(summary["baseline_count"], 1)

    # ── 3. API Endpoints ──────────────────────────────────────────────────────

    def test_api_save_and_summary_lifecycle(self):
        # 1. Save run via POST /api/analytics/save
        payload = {
            "scenario_id": "scenario_001",
            "strategy": "AI_ASSISTED",
            "throughput": 5,
            "average_delay": 3.5,
            "p1_delay": 0.0,
            "waiting_time": 8.0,
            "conflict_count": 0,
            "utilization": 1.0,
        }
        save_res = self.client.post("/api/analytics/save", json=payload)
        self.assertEqual(save_res.status_code, 200)
        self.assertTrue(save_res.json()["success"])

        # 2. Get summary via GET /api/analytics/summary
        sum_res = self.client.get("/api/analytics/summary")
        self.assertEqual(sum_res.status_code, 200)
        sum_data = sum_res.json()
        self.assertTrue(sum_data["success"])
        self.assertGreaterEqual(sum_data["data"]["total_runs"], 1)

        # 3. List runs via GET /api/analytics/runs
        runs_res = self.client.get("/api/analytics/runs")
        self.assertEqual(runs_res.status_code, 200)
        runs_data = runs_res.json()
        self.assertTrue(runs_data["success"])
        self.assertGreaterEqual(runs_data["data"]["total"], 1)

        # 4. Clear history via DELETE /api/analytics/history
        del_res = self.client.delete("/api/analytics/history")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()["success"])


if __name__ == "__main__":
    unittest.main()
