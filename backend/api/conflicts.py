from fastapi import APIRouter

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])


@router.get("")
def get_conflicts(severity: str | None = None, conflict_type: str | None = None,
                  location: str | None = None, train_id: str | None = None):
    """Phase 1 stub — returns empty list with correct envelope. Powered by AI in Phase 2."""
    return {
        "success": True,
        "data": {"conflicts": [], "total": 0,
                 "message": "Conflict detection will be active in Phase 2 (AI layer)."},
        "error": None,
    }
