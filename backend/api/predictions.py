"""
RAILOPTIX — Predictions API
============================
Endpoints:
  POST /api/predictions          -> Full prediction pass (all trains + all sections)
  GET  /api/predictions/train/{train_id}  -> Single train delay prediction
  GET  /api/predictions/section/{section_id} -> Section congestion prediction
  GET  /api/predictions/status   -> Model load status
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional

from ..services.prediction.delay_predictor import predictor
from ..services.twin.digital_twin import digital_twin
from ..services.twin.network_graph import rail_network

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


class PredictionRequest(BaseModel):
    horizon_minutes: int = 30       # How far ahead to predict (informational)
    include_sections: bool = True   # Include section congestion predictions


# ─────────────────────────────────────────────────────────────────────────────

@router.post("", summary="Full prediction pass — all trains + all sections")
def run_predictions(body: PredictionRequest):
    """
    Runs the XGBoost prediction engine over the current Digital Twin state.
    Returns:
      - Per-train delay predictions with trend labels
      - Per-section congestion risk with severity levels
      - Network summary stats
    Falls back to heuristic model if XGBoost .json files are not yet placed
    in backend/ml_models/ (safe for dev/demo before Colab training).
    """
    twin_state = digital_twin.get_state()

    if not twin_state.get("trains"):
        return {
            "success": True,
            "data": {
                "train_predictions": [],
                "section_congestion": {},
                "summary": {
                    "avg_predicted_delay_min": 0.0,
                    "at_risk_sections": [],
                    "at_risk_count": 0,
                    "trains_predicted": 0,
                    "model_loaded": predictor.is_model_loaded,
                    "message": "No active scenario — load a scenario first.",
                },
                "horizon_minutes": body.horizon_minutes,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "error": None,
        }

    result = predictor.predict_all(twin_state)

    if not body.include_sections:
        result["section_congestion"] = {}

    return {
        "success": True,
        "data": {
            **result,
            "horizon_minutes": body.horizon_minutes,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "error": None,
    }


@router.get("/train/{train_id}", summary="Predict delay for a single train")
def predict_train(train_id: str):
    """Get delay prediction for one specific train."""
    train = digital_twin.get_train(train_id)
    if not train:
        raise HTTPException(status_code=404, detail=f"Train '{train_id}' not found in Digital Twin.")

    all_trains    = digital_twin.get_all_trains()
    occupancy_map = digital_twin.get_section_occupancy()

    result = predictor.predict_train_delay(train, all_trains, occupancy_map)

    return {
        "success": True,
        "data": {
            **result,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "error": None,
    }


@router.get("/section/{section_id}", summary="Predict congestion risk for a section")
def predict_section(section_id: str):
    """Get congestion risk prediction for one network section."""
    if section_id not in rail_network.sections:
        raise HTTPException(status_code=404, detail=f"Section '{section_id}' not in network.")

    all_trains    = digital_twin.get_all_trains()
    occupancy_map = digital_twin.get_section_occupancy()

    result = predictor.predict_section_congestion(section_id, all_trains, occupancy_map)

    return {
        "success": True,
        "data": {
            **result,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "error": None,
    }


@router.get("/status", summary="Check if XGBoost model files are loaded")
def model_status():
    """
    Returns whether the trained XGBoost models are loaded.
    If 'model_loaded' is false, predictions use the heuristic fallback.
    To enable XGBoost: train on Colab, place .json files in backend/ml_models/
    """
    from pathlib import Path
    ml_dir = Path(__file__).resolve().parents[1] / "ml_models"

    delay_exists = (ml_dir / "delay_model.json").exists()
    cong_exists  = (ml_dir / "congestion_model.json").exists()
    meta_exists  = (ml_dir / "feature_columns.json").exists()

    return {
        "success": True,
        "data": {
            "xgboost_loaded":          predictor.is_model_loaded,
            "ml_models_dir":           str(ml_dir),
            "delay_model_present":     delay_exists,
            "congestion_model_present": cong_exists,
            "feature_metadata_present": meta_exists,
            "prediction_mode":         "xgboost" if predictor.is_model_loaded else "heuristic_fallback",
            "model_info":              predictor._model_info,
            "instructions": (
                "Place delay_model.json, congestion_model.json, feature_columns.json "
                "from Colab into backend/ml_models/ to enable XGBoost predictions."
            ) if not delay_exists else "XGBoost models are active.",
        },
        "error": None,
    }
