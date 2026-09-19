import unittest
import time
from fastapi.testclient import TestClient
from backend.main import app


class TestAPIAndSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_ctx = TestClient(app)
        cls.client = cls.client_ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_ctx.__exit__(None, None, None)

    def test_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertTrue(data.get("network_loaded"))

    def test_network_topology(self):
        res = self.client.get("/api/network")
        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertTrue(json_data["success"])
        self.assertEqual(len(json_data["data"]["nodes"]), 11)
        self.assertEqual(len(json_data["data"]["sections"]), 10)
        self.assertEqual(len(json_data["data"]["routes"]), 5)

    def test_scenarios_and_twin_state(self):
        # List scenarios
        res = self.client.get("/api/scenarios")
        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertTrue(json_data["success"])
        scenarios = json_data["data"]["scenarios"]
        self.assertGreaterEqual(len(scenarios), 1)

        # Load scenario_001
        res = self.client.post("/api/scenarios/load", json={"scenario_id": "scenario_001"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Check Twin State
        res = self.client.get("/api/twin/state")
        self.assertEqual(res.status_code, 200)
        state = res.json()["data"]
        self.assertEqual(state["scenario_id"], "scenario_001")
        self.assertEqual(len(state["trains"]), 5)

    def test_simulation_lifecycle(self):
        # Load scenario first
        self.client.post("/api/scenarios/load", json={"scenario_id": "scenario_001"})

        # Start simulation
        res = self.client.post("/api/simulation/start")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Speed up
        res = self.client.post("/api/simulation/speed", json={"multiplier": 10.0})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Let simulation advance
        time.sleep(0.5)

        # Check status
        res = self.client.get("/api/simulation/status")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Check KPIs
        res = self.client.get("/api/simulation/kpis")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Pause
        res = self.client.post("/api/simulation/pause")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Reset
        res = self.client.post("/api/simulation/reset")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])


if __name__ == "__main__":
    unittest.main()
