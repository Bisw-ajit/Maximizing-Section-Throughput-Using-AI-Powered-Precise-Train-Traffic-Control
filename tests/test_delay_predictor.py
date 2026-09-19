"""
RAILOPTIX — Test: XGBoost Delay & Congestion Predictor
=======================================================
Verifies that:
  - The XGBoost models load correctly from backend/ml_models/
  - predict_train_delay() returns a correctly-structured dict
  - predict_section_congestion() returns a correctly-structured dict
  - predict_all() runs over a populated digital twin
  - The heuristic fallback is well-behaved (non-negative, bounded output)
"""
import unittest
from unittest.mock import patch

from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.services.twin.digital_twin import digital_twin
from backend.services.prediction.delay_predictor import DelayPredictor, predictor
from backend.services.prediction.feature_engineering import (
    build_delay_features,
    build_congestion_features,
)


NETWORK_PATH = "scenarios/network/railoptix_network.json"


class TestDelayPredictorModel(unittest.TestCase):
    """Tests for the XGBoost predictor (model files present in backend/ml_models/)."""

    @classmethod
    def setUpClass(cls):
        if not rail_network.is_loaded():
            rail_network.load_from_json(NETWORK_PATH)
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)
        digital_twin.load_scenario(scenario, timetable)

    # ── Model loading ─────────────────────────────────────────────────────────

    def test_model_loaded(self):
        """XGBoost .json files in backend/ml_models/ must be loaded at startup."""
        self.assertTrue(
            predictor.is_model_loaded,
            "XGBoost model should be loaded — ensure delay_model.json and "
            "congestion_model.json exist in backend/ml_models/"
        )

    def test_model_info_structure(self):
        """Model info is stored in feature_columns.json and must have expected structure."""
        import json
        from pathlib import Path
        meta_path = Path("backend/ml_models/feature_columns.json")
        self.assertTrue(meta_path.exists(), "feature_columns.json must exist in backend/ml_models/")
        info = json.loads(meta_path.read_text())
        self.assertIn("delay_model", info)
        self.assertIn("congestion_model", info)
        self.assertEqual(info["delay_model"]["model_type"], "XGBRegressor")
        self.assertEqual(info["congestion_model"]["model_type"], "XGBClassifier")
        # Verify reported metrics are plausible
        self.assertGreater(info["delay_model"]["metrics"]["r2"], 0.90)
        self.assertGreater(info["congestion_model"]["metrics"]["roc_auc"], 0.95)

    # ── predict_train_delay() ─────────────────────────────────────────────────

    def test_predict_train_delay_structure(self):
        """predict_train_delay() must return a dict with required keys."""
        train = digital_twin.get_train("T001")
        self.assertIsNotNone(train)
        all_trains = digital_twin.get_all_trains()
        occupancy = digital_twin.get_section_occupancy()

        result = predictor.predict_train_delay(train, all_trains, occupancy)

        # Keys verified against actual predictor output
        required_keys = [
            "train_id", "train_number",
            "current_delay_min", "predicted_delay_min",
            "delay_delta_min", "trend", "model_used",
        ]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_predict_train_delay_non_negative(self):
        """Predicted delay must always be ≥ 0."""
        train = digital_twin.get_train("T001")
        all_trains = digital_twin.get_all_trains()
        occupancy = digital_twin.get_section_occupancy()
        result = predictor.predict_train_delay(train, all_trains, occupancy)
        self.assertGreaterEqual(result["predicted_delay_min"], 0.0)

    def test_predict_train_delay_trend_valid(self):
        """trend must be one of the valid labels."""
        train = digital_twin.get_train("T001")
        all_trains = digital_twin.get_all_trains()
        occupancy = digital_twin.get_section_occupancy()
        result = predictor.predict_train_delay(train, all_trains, occupancy)
        self.assertIn(result["trend"], ["IMPROVING", "STABLE", "WORSENING"])

    # ── predict_section_congestion() ──────────────────────────────────────────

    def test_predict_section_congestion_structure(self):
        """predict_section_congestion() must return required keys."""
        all_trains = digital_twin.get_all_trains()
        occupancy = digital_twin.get_section_occupancy()
        result = predictor.predict_section_congestion("KUR-SIL", all_trains, occupancy)

        # Keys verified against actual predictor output
        required_keys = [
            "section_id", "congestion_risk", "risk_probability",
            "severity", "model_used",
        ]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_predict_section_congestion_probability_bounded(self):
        """Congestion probability must be in [0.0, 1.0]."""
        all_trains = digital_twin.get_all_trains()
        occupancy = digital_twin.get_section_occupancy()
        result = predictor.predict_section_congestion("KUR-BALU", all_trains, occupancy)
        self.assertGreaterEqual(result["risk_probability"], 0.0)
        self.assertLessEqual(result["risk_probability"], 1.0)

    # ── predict_all() ─────────────────────────────────────────────────────────

    def test_predict_all_structure(self):
        """predict_all() must return train_predictions and section_congestion."""
        state = digital_twin.get_state()
        result = predictor.predict_all(state)

        self.assertIn("train_predictions", result)
        self.assertIn("section_congestion", result)
        self.assertIn("summary", result)
        self.assertIsInstance(result["train_predictions"], list)

    def test_predict_all_covers_all_trains(self):
        """predict_all() must return one prediction per active train."""
        state = digital_twin.get_state()
        result = predictor.predict_all(state)
        active_train_count = len(state["trains"])
        self.assertEqual(len(result["train_predictions"]), active_train_count)


class TestDelayPredictorHeuristicFallback(unittest.TestCase):
    """Tests for the heuristic fallback (simulated model-not-loaded scenario)."""

    def _make_delay_features(self, **overrides) -> dict:
        base = {
            "current_delay_min": 5.0,
            "section_length_km": 18.0,
            "section_capacity": 1.0,
            "section_occupancy": 1.0,
            "is_single_track": 1.0,
            "train_priority": 2.0,
            "speed_kmh": 68.0,
            "time_of_day_min": 480.0,     # 8 AM = peak
            "is_peak_hour": 1.0,
            "trains_ahead": 0.0,
            "journey_progress": 0.3,
            "sched_vs_actual_diff": 5.0,
            "congestion_ratio": 1.0,
            "speed_limit_kmh": 80.0,
        }
        base.update(overrides)
        return base

    def test_heuristic_delay_non_negative(self):
        """Heuristic delay fallback must never return negative delay."""
        features = self._make_delay_features(current_delay_min=0.0)
        result = DelayPredictor._heuristic_delay(features)
        self.assertGreaterEqual(result, 0.0)

    def test_heuristic_delay_increases_with_congestion(self):
        """Single-track over-capacity must increase predicted delay."""
        low = self._make_delay_features(section_occupancy=0.0, current_delay_min=0.0)
        high = self._make_delay_features(
            section_occupancy=2.0, is_single_track=1.0,
            section_capacity=1.0, current_delay_min=0.0
        )
        self.assertGreater(
            DelayPredictor._heuristic_delay(high),
            DelayPredictor._heuristic_delay(low),
        )

    def test_heuristic_congestion_bounded(self):
        """Heuristic congestion probability must be in [0.0, 1.0]."""
        features = {
            "congestion_ratio": 1.5,
            "future_load": 1.0,
            "is_peak_hour": 1.0,
            "is_single_track": 1.0,
        }
        result = DelayPredictor._heuristic_congestion(features)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)


class TestFeatureEngineering(unittest.TestCase):
    """Tests for the feature vector builders."""

    @classmethod
    def setUpClass(cls):
        if not rail_network.is_loaded():
            rail_network.load_from_json(NETWORK_PATH)
        scenario = scenario_loader.load("scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)
        digital_twin.load_scenario(scenario, timetable)

    def test_delay_features_all_keys_present(self):
        """build_delay_features() must return all 14 expected feature keys."""
        EXPECTED = [
            "current_delay_min", "section_length_km", "section_capacity",
            "section_occupancy", "is_single_track", "train_priority",
            "speed_kmh", "time_of_day_min", "is_peak_hour",
            "trains_ahead", "journey_progress", "sched_vs_actual_diff",
            "congestion_ratio", "speed_limit_kmh",
        ]
        train = digital_twin.get_train("T001")
        all_trains = digital_twin.get_all_trains()
        occupancy = digital_twin.get_section_occupancy()
        features = build_delay_features(train, all_trains, occupancy)
        for key in EXPECTED:
            self.assertIn(key, features, f"Missing feature: {key}")

    def test_congestion_features_all_keys_present(self):
        """build_congestion_features() must return all 12 expected feature keys."""
        EXPECTED = [
            "section_length_km", "section_capacity", "section_occupancy",
            "is_single_track", "trains_approaching", "time_of_day_min",
            "is_peak_hour", "avg_delay_in_section", "congestion_ratio",
            "future_load", "total_trains_network", "speed_limit_kmh",
        ]
        all_trains = digital_twin.get_all_trains()
        occupancy = digital_twin.get_section_occupancy()
        features = build_congestion_features("KUR-SIL", occupancy, all_trains)
        for key in EXPECTED:
            self.assertIn(key, features, f"Missing feature: {key}")

    def test_congestion_ratio_bounded(self):
        """congestion_ratio must be non-negative."""
        train = digital_twin.get_train("T001")
        all_trains = digital_twin.get_all_trains()
        occupancy = digital_twin.get_section_occupancy()
        features = build_delay_features(train, all_trains, occupancy)
        self.assertGreaterEqual(features["congestion_ratio"], 0.0)


if __name__ == "__main__":
    unittest.main()
