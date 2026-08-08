from fastapi import APIRouter

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("")
def get_recommendations(body: dict):
    """Phase 1 stub — AI decision engine wired in Phase 2."""
    return {
        "success": True,
        "data": {
            "candidates": [],
            "recommended": None,
            "total_candidates": 0,
            "feasible_count": 0,
            "message": "AI decision engine will be active in Phase 2.",
        },
        "error": None,
    }
