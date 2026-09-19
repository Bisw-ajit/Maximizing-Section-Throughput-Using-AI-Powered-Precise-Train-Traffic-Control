"""
RAILOPTIX — Delay Predictor Service
=====================================
Loads pre-trained XGBoost models from backend/ml_models/ and runs inference.

Models loaded at startup (lazy singleton pattern):
  - delay_model.json      : XGBRegressor  -> predicted next delay (minutes)
  - congestion_model.json : XGBClassifier -> congestion risk (0 / 1) + probability

Usage:
  from .delay_predictor import predictor
  result = predictor.predict_train_delay(train, all_trains, occupancy_map)
  result = predictor.predict_section_congestion(section_id, all_trains, occupancy_map)
  result = predictor.predict_all(twin_state)
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("railoptix.predictor")

# Model directory — place your Colab-trained files here
ML_MODELS_DIR = Path(__file__).resolve().parents[2] / "ml_models"

# Feature column order (must match training)
DELAY_FEATURES = [
    "current_delay_min", "section_length_km", "section_capacity",
    "section_occupancy", "is_single_track", "train_priority", "speed_kmh",
    "time_of_day_min", "is_peak_hour", "trains_ahead", "journey_progress",
    "sched_vs_actual_diff", "congestion_ratio", "speed_limit_kmh",
]
CONG_FEATURES = [
    "section_length_km", "section_capacity", "section_occupancy",
    "is_single_track", "trains_approaching", "time_of_day_min",
    "is_peak_hour", "avg_delay_in_section", "congestion_ratio",
    "future_load", "total_trains_network", "speed_limit_kmh",
]


class DelayPredictor:
    """
    Lazy-loading XGBoost inference service.
    Falls back to heuristic model if .json model files are not found.
    """

    def __init__(self):
        self._delay_model = None
        self._cong_model  = None
        self._loaded      = False
        self._model_info  = {}

    # ── Model Loading ─────────────────────────────────────────────────────────

    def _load_models(self):
        if self._loaded:
            return
        try:
            import xgboost as xgb

            delay_path = ML_MODELS_DIR / "delay_model.json"
            cong_path  = ML_MODELS_DIR / "congestion_model.json"
            meta_path  = ML_MODELS_DIR / "feature_columns.json"

            if not delay_path.exists() or not cong_path.exists():
                logger.warning(
                    "XGBoost model files not found in %s — using heuristic fallback. "
                    "Train models on Colab and place .json files there.", ML_MODELS_DIR
                )
                self._loaded = True
                return

            self._delay_model = xgb.XGBRegressor()
            self._delay_model.load_model(str(delay_path))

            self._cong_model = xgb.XGBClassifier()
            self._cong_model.load_model(str(cong_path))

            if meta_path.exists():
                with open(meta_path) as f:
                    self._model_info = json.load(f)

            logger.info("XGBoost models loaded from %s", ML_MODELS_DIR)

        except ImportError:
            logger.warning("xgboost not installed — using heuristic fallback. "
                           "Run: pip install xgboost")
        finally:
            self._loaded = True

    @property
    def is_model_loaded(self) -> bool:
        self._load_models()
        return self._delay_model is not None

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict_train_delay(
        self,
        train,                       # TrainState
        all_trains: list,
        occupancy_map: dict,
    ) -> dict:
        """Predict next-station delay for a single train."""
        self._load_models()
        from .feature_engineering import build_delay_features

        features = build_delay_features(train, all_trains, occupancy_map)

        if self._delay_model is not None:
            import numpy as np
            X = np.array([[features[col] for col in DELAY_FEATURES]])
            predicted_delay = float(self._delay_model.predict(X)[0])
        else:
            # Heuristic fallback (no model file)
            predicted_delay = self._heuristic_delay(features)

        predicted_delay = max(0.0, round(predicted_delay, 2))
        delta = predicted_delay - train.delay_minutes

        return {
            "train_id":          train.train_id,
            "train_number":      train.train_number,
            "current_delay_min": train.delay_minutes,
            "predicted_delay_min": predicted_delay,
            "delay_delta_min":   round(delta, 2),
            "trend":             "WORSENING" if delta > 2 else "IMPROVING" if delta < -2 else "STABLE",
            "model_used":        "xgboost" if self._delay_model is not None else "heuristic",
        }

    def predict_section_congestion(
        self,
        section_id: str,
        all_trains: list,
        occupancy_map: dict,
    ) -> dict:
        """Predict congestion risk for a network section."""
        self._load_models()
        from .feature_engineering import build_congestion_features

        features = build_congestion_features(section_id, occupancy_map, all_trains)

        if self._cong_model is not None:
            import numpy as np
            X = np.array([[features[col] for col in CONG_FEATURES]])
            risk_prob  = float(self._cong_model.predict_proba(X)[0][1])
            risk_label = int(self._cong_model.predict(X)[0])
        else:
            risk_prob  = self._heuristic_congestion(features)
            risk_label = int(risk_prob >= 0.5)

        severity = (
            "CRITICAL" if risk_prob >= 0.75
            else "WARNING" if risk_prob >= 0.5
            else "ADVISORY" if risk_prob >= 0.30
            else "CLEAR"
        )

        return {
            "section_id":      section_id,
            "congestion_risk": risk_label,
            "risk_probability": round(risk_prob, 3),
            "severity":        severity,
            "model_used":      "xgboost" if self._cong_model is not None else "heuristic",
        }

    def predict_all(self, twin_state: dict) -> dict:
        """
        Run full prediction pass over the entire Digital Twin state.
        Called by the /api/predictions endpoint.
        """
        from ...services.twin.digital_twin import digital_twin
        from ...services.twin.network_graph import rail_network

        all_trains    = digital_twin.get_all_trains()
        occupancy_map = digital_twin.get_section_occupancy()

        # Per-train delay predictions
        train_predictions = []
        for train in all_trains:
            if train.status not in ("SCHEDULED", "RUNNING", "DELAYED"):
                continue
            pred = self.predict_train_delay(train, all_trains, occupancy_map)
            train_predictions.append(pred)

        # Per-section congestion predictions
        section_congestion = {}
        for section_id in rail_network.sections:
            if "-" not in section_id:  # skip reverse edge duplicates
                continue
            pred = self.predict_section_congestion(section_id, all_trains, occupancy_map)
            section_congestion[section_id] = pred

        # Summary stats
        delays = [p["predicted_delay_min"] for p in train_predictions]
        avg_predicted_delay = sum(delays) / len(delays) if delays else 0.0
        at_risk_sections = [
            sid for sid, c in section_congestion.items()
            if c["congestion_risk"] == 1
        ]

        return {
            "train_predictions":   train_predictions,
            "section_congestion":  section_congestion,
            "summary": {
                "avg_predicted_delay_min": round(avg_predicted_delay, 2),
                "at_risk_sections":        at_risk_sections,
                "at_risk_count":           len(at_risk_sections),
                "trains_predicted":        len(train_predictions),
                "model_loaded":            self.is_model_loaded,
                "model_info":              self._model_info,
            },
        }

    # ── Heuristic Fallbacks (no model file) ───────────────────────────────────

    @staticmethod
    def _heuristic_delay(features: dict) -> float:
        """
        Simple rule-based delay estimate used when model files are absent.
        Good enough for demo/dev; replace with trained model for production.
        """
        nd = features["current_delay_min"]
        congestion = max(0, features["section_occupancy"] - features["section_capacity"] + 1)
        nd += congestion * 5.0
        if features["is_single_track"] and features["section_occupancy"] >= features["section_capacity"]:
            nd += 10.0
        if features["is_peak_hour"]:
            nd += 3.0
        nd -= (6 - features["train_priority"]) * 1.0
        nd += features["trains_ahead"] * 2.5
        return max(0.0, nd)

    @staticmethod
    def _heuristic_congestion(features: dict) -> float:
        """Rule-based congestion probability when model file is absent."""
        score = 0.0
        score += features["congestion_ratio"] * 0.4
        score += features["future_load"] * 0.3
        score += features["is_peak_hour"] * 0.15
        score += features["is_single_track"] * 0.15
        return min(1.0, score)


# Singleton — loaded once at app startup (lazy)
predictor = DelayPredictor()
