"""
Unit and Integration Tests for RAIL-7:
Live Train Telemetry Ingestion & RailRadar Data Adapter
"""

import unittest
import asyncio
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.twin.network_graph import rail_network
from backend.services.twin.digital_twin import digital_twin, DataSource
from backend.services.twin.network_mapper import (
    canonical_station,
    deduce_route_and_direction,
    deduce_section,
    calculate_journey_progress,
)
from backend.providers.railradar.adapter import (
    RailRadarAdapter,
    RealisticCorridorFeeder,
)


class TestRail7LiveAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")
        cls.client = TestClient(app)

    def setUp(self):
        digital_twin.reset()

    # ── 1. Test Network Mapper ───────────────────────────────────────────────

    def test_canonical_station_alias(self):
        self.assertEqual(canonical_station("Bhubaneswar"), "BBS")
        self.assertEqual(canonical_station("CTK"), "CTK")
        self.assertEqual(canonical_station("Khurda Road Jn"), "KUR")
        self.assertEqual(canonical_station("Puri Terminus"), "PURI")
        self.assertEqual(canonical_station("Berhampur"), "BAM")
        self.assertIsNone(canonical_station("NON_EXISTENT_STATION"))

    def test_route_and_direction_deduction(self):
        route_id, direction = deduce_route_and_direction("CTK", "BBS", "PURI")
        self.assertEqual(route_id, "route_A")
        self.assertEqual(direction, "SOUTHBOUND")

        route_id, direction = deduce_route_and_direction("PURI", "SIL", "CTK")
        self.assertEqual(route_id, "route_C")
        self.assertEqual(direction, "NORTHBOUND")

    def test_section_and_progress_calculation(self):
        sec = deduce_section("BBS", "RET")
        self.assertEqual(sec, "BBS-RET")

        sec = deduce_section("KUR", "SIL")
        self.assertEqual(sec, "KUR-SIL")

        progress = calculate_journey_progress("route_A", "CTK")
        self.assertEqual(progress, 0.0)

        progress = calculate_journey_progress("route_A", "PURI")
        self.assertEqual(progress, 1.0)

    # ── 2. Test Corridor Feeder & RailRadar Adapter ──────────────────────────

    def test_corridor_feeder_generation(self):
        feeder = RealisticCorridorFeeder()
        records = asyncio.run(feeder.fetch_trains())
        self.assertGreaterEqual(len(records), 5)

        vande_bharat = next((r for r in records if r["train_number"] == "20836"), None)
        self.assertIsNotNone(vande_bharat)
        self.assertTrue(vande_bharat["is_live"])
        self.assertEqual(vande_bharat["source"], "ecor_live_stream")
        self.assertIn(vande_bharat["current_node"], ["SIL", "PURI", "KUR"])
        self.assertIsNotNone(vande_bharat["current_section"])

    def test_railradar_caching_and_fallback(self):
        adapter = RailRadarAdapter(api_key="", enable_mock_fallback=True)
        records_1 = asyncio.run(adapter.fetch_trains())
        self.assertGreater(len(records_1), 0)
        self.assertEqual(adapter.active_source, "corridor_live_feeder")
        self.assertTrue(adapter.is_cache_valid)

        # Subsequent fetch within TTL should hit cache
        records_2 = asyncio.run(adapter.fetch_trains(force_refresh=False))
        self.assertEqual(len(records_1), len(records_2))

    # ── 3. Test Digital Twin Ingestion ───────────────────────────────────────

    def test_digital_twin_sync(self):
        feeder = RealisticCorridorFeeder()
        records = asyncio.run(feeder.fetch_trains())

        stats = digital_twin.update_from_live(records)
        self.assertEqual(stats["added"], len(records))

        trains = digital_twin.get_all_trains()
        self.assertEqual(len(trains), len(records))

        # Test inspection of ingested train
        vb = digital_twin.get_train("LIVE_20836")
        self.assertIsNotNone(vb)
        self.assertEqual(vb.train_number, "20836")
        self.assertEqual(vb.data_source, DataSource.LIVE)
        self.assertTrue(vb.is_live)

        # Test section occupancy updated
        occupancy = digital_twin.get_section_occupancy()
        self.assertGreater(len(occupancy), 0)

    # ── 4. Test API Endpoints ────────────────────────────────────────────────

    def test_api_live_trains(self):
        res = self.client.get("/api/trains/live")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload["success"])
        self.assertGreater(payload["data"]["total"], 0)
        self.assertTrue(payload["data"]["is_live"])

    def test_api_provider_status(self):
        res = self.client.get("/api/trains/live/provider-status")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["provider"], "RailRadar")
        self.assertTrue(payload["data"]["mock_fallback_enabled"])

    def test_api_force_sync(self):
        res = self.client.post("/api/trains/live/sync")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload["success"])
        self.assertIn("sync_stats", payload["data"])
        self.assertGreater(payload["data"]["active_trains_count"], 0)

    def test_api_get_train_detail(self):
        # First sync live trains
        self.client.post("/api/trains/live/sync")

        # Query by train_number (e.g. 20836 Vande Bharat)
        res = self.client.get("/api/trains/20836")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["train_number"], "20836")
        self.assertEqual(payload["data"]["data_source"], "LIVE")


if __name__ == "__main__":
    unittest.main()
