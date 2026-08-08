from fastapi import APIRouter

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/compare")
def compare_runs():
    """Phase 1 stub — KPI comparison wired in Phase 2 after simulation runs."""
    return {
        "success": True,
        "data": {
            "baseline": None,
            "ai_assisted": None,
            "runs": [],
            "delay_improvement_pct": None,
            "conflict_reduction_pct": None,
            "throughput_improvement_pct": None,
            "message": "Run at least one BASELINE and one AI_ASSISTED simulation to compare.",
        },
        "error": None,
    }


@router.get("/runs")
def list_runs():
    return {"success": True, "data": {"runs": []}, "error": None}
