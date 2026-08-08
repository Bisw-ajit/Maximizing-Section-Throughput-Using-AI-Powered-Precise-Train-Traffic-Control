from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.post("")
def predict(body: dict):
    """Phase 1 stub — XGBoost prediction service wired in Phase 2."""
    return {
        "success": True,
        "data": {
            "predictions": [],
            "section_congestion": {},
            "horizon_minutes": body.get("horizon_minutes", 30),
            "generated_at": datetime.utcnow().isoformat(),
            "message": "Prediction engine will be active in Phase 2.",
        },
        "error": None,
    }
