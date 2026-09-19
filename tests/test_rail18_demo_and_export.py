"""
Unit and Integration Tests for RAIL-18:
Demo Autoplay Mode, PDF/CSV Export & Dispatch Audit Log Inspector
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.twin.network_graph import rail_network
from backend.services.analytics.report_exporter import report_exporter
from backend.services.analytics.audit_logger import audit_logger, AuditCategory


class TestRail18DemoAndExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rail_network.load_from_json("scenarios/network/railoptix_network.json")
        cls.client = TestClient(app)

    def test_audit_logger_direct(self):
        """Test audit logger event logging, category filtering, and train filtering."""
        entry = audit_logger.log_event(
            category=AuditCategory.CONTROLLER_ACTION,
            event_type="PRIORITY_OVERRIDE",
            location="KUR",
            message="Test priority override for unit test",
            train_id="TEST_TRAIN_99",
            details={"priority": 1}
        )
        self.assertEqual(entry.category, "CONTROLLER_ACTION")
        self.assertEqual(entry.train_id, "TEST_TRAIN_99")
        self.assertEqual(entry.location, "KUR")

        # Retrieve all
        all_entries = audit_logger.get_entries(limit=100)
        self.assertGreaterEqual(len(all_entries), 1)

        # Filter by category
        filtered = audit_logger.get_entries(category="CONTROLLER_ACTION")
        self.assertTrue(all(e["category"] == "CONTROLLER_ACTION" for e in filtered))

        # Filter by train_id
        train_filtered = audit_logger.get_entries(train_id="TEST_TRAIN_99")
        self.assertEqual(len(train_filtered), 1)
        self.assertEqual(train_filtered[0]["train_id"], "TEST_TRAIN_99")

    def test_report_exporter_csv(self):
        """Test CSV report generation content and columns."""
        csv_content = report_exporter.generate_csv_report("scenario_001")
        self.assertIsInstance(csv_content, str)
        self.assertIn("# RAILOPTIX DISPATCH SIMULATION REPORT", csv_content)
        self.assertIn("--- KPI BENCHMARK SUMMARY ---", csv_content)
        self.assertIn("--- INDIVIDUAL TRAIN PERFORMANCE LOG ---", csv_content)
        self.assertIn("Train ID,Train Number,Train Name,Priority", csv_content)
        self.assertIn("T001", csv_content)

    def test_report_exporter_html(self):
        """Test printable HTML report generation."""
        html_content = report_exporter.generate_html_pdf_report("scenario_001")
        self.assertIsInstance(html_content, str)
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("RAILOPTIX Dispatch Simulation Report", html_content)
        self.assertIn("East Coast Railway (ECoR)", html_content)
        self.assertIn("@media print", html_content)
        self.assertIn("Macro Benchmark Comparison", html_content)
        self.assertIn("Applied AI Interventions", html_content)

    def test_api_export_csv_endpoint(self):
        """Verify GET /api/analytics/export/csv returns valid downloadable CSV."""
        resp = self.client.get("/api/analytics/export/csv?scenario_id=scenario_001")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", resp.headers.get("content-disposition", ""))
        self.assertIn("# RAILOPTIX DISPATCH SIMULATION REPORT", resp.text)
        self.assertIn("--- KPI BENCHMARK SUMMARY ---", resp.text)

    def test_api_export_report_endpoint(self):
        """Verify GET /api/analytics/export/report returns valid printable HTML."""
        resp = self.client.get("/api/analytics/export/report?scenario_id=scenario_001")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers.get("content-type"))
        self.assertIn("RAILOPTIX Dispatch Simulation Report", resp.text)
        self.assertIn("Executive Simulation & Dispatch Evaluation Report", resp.text)

    def test_api_audit_log_endpoint(self):
        """Verify GET /api/analytics/audit-log returns JSON audit trail with category filtering."""
        resp = self.client.get("/api/analytics/audit-log?limit=50")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        entries = data["data"]["entries"]
        self.assertGreater(len(entries), 0)

        # Filter query
        resp_filtered = self.client.get("/api/analytics/audit-log?category=CONFLICT_ALERT")
        self.assertEqual(resp_filtered.status_code, 200)
        data_filtered = resp_filtered.json()
        for entry in data_filtered["data"]["entries"]:
            self.assertEqual(entry["category"], "CONFLICT_ALERT")
