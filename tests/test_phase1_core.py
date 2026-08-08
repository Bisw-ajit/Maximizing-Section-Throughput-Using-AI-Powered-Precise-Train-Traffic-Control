import unittest
import asyncio
from datetime import datetime

from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.services.twin.digital_twin import digital_twin


class TestPhase1Core(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")

    def test_network_graph_loaded(self):
        self.assertTrue(rail_network.is_loaded())
        nodes = rail_network.get_all_nodes()
        self.assertEqual(len(nodes), 6)
        sections = rail_network.get_all_sections()
        self.assertEqual(len(sections), 5)
        routes = rail_network.get_all_routes()
        self.assertEqual(len(routes), 5)

    def test_scenario_loader_and_timetable(self):
        scenario = scenario_loader.load("scenario_001", rail_network)
        self.assertEqual(scenario["scenario_id"], "scenario_001")
        self.assertEqual(len(scenario["trains"]), 5)

        timetable = scenario_loader.compute_timetable(scenario, rail_network)
        self.assertIn("T001", timetable)
        self.assertIn("CTK", timetable["T001"])
        self.assertIn("BBS", timetable["T001"])

    def test_digital_twin_state(self):
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)
        digital_twin.load_scenario(scenario, timetable)

        state = digital_twin.get_state()
        self.assertEqual(state["scenario_id"], "scenario_001")
        self.assertEqual(len(state["trains"]), 5)

        # Test state update
        digital_twin.update_train_state("T001", delay_minutes=12.5, status="DELAYED")
        t001 = digital_twin.get_train("T001")
        self.assertEqual(t001.delay_minutes, 12.5)
        self.assertEqual(t001.status, "DELAYED")


if __name__ == "__main__":
    unittest.main()
