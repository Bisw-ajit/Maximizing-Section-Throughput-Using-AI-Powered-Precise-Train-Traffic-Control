"""
RAILOPTIX — Conflicts API Router
=================================
Endpoints:
  GET /api/conflicts                       -> List all active & predicted conflicts
  GET /api/conflicts/{conflict_id}            -> Detail of specific conflict
  GET /api/conflicts/{conflict_id}/candidates -> Generate AI candidate actions for this conflict
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..services.conflict.conflict_detector import conflict_detector
from ..services.decision.action_generator import action_generator

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])


@router.get("", summary="List all active and predicted network conflicts")
def get_conflicts(
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    conflict_type: Optional[str] = Query(None, description="Filter by type: JUNCTION_CONFLICT, CROSSING_CONFLICT, etc."),
    location: Optional[str] = Query(None, description="Filter by location: e.g. KUR, SIL-PURI"),
    train_id: Optional[str] = Query(None, description="Filter by train ID: e.g. T001"),
):
    """
    Scans the Digital Twin state and schedule for conflicts:
    - Junction convergence contention
    - Single-line crossing standoffs
    - Section capacity / headway compression
    """
    conflicts = conflict_detector.detect_all()

    # Apply filters
    if severity:
        conflicts = [c for c in conflicts if c.severity.value == severity.upper()]
    if conflict_type:
        conflicts = [c for c in conflicts if c.conflict_type.value == conflict_type.upper()]
    if location:
        conflicts = [c for c in conflicts if location.upper() in c.location.upper()]
    if train_id:
        conflicts = [c for c in conflicts if train_id in c.train_ids]

    return {
        "success": True,
        "data": {
            "conflicts": [c.to_dict() for c in conflicts],
            "total": len(conflicts),
            "critical_count": sum(1 for c in conflicts if c.severity.value == "CRITICAL"),
            "high_count": sum(1 for c in conflicts if c.severity.value == "HIGH"),
        },
        "error": None,
    }


@router.get("/{conflict_id}", summary="Get conflict detail")
def get_conflict_detail(conflict_id: str):
    """Get full diagnostic information on a specific conflict."""
    conflicts = conflict_detector.detect_all()
    match = next((c for c in conflicts if c.conflict_id == conflict_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Conflict '{conflict_id}' not found.")

    return {
        "success": True,
        "data": match.to_dict(),
        "error": None,
    }


@router.get("/{conflict_id}/candidates", summary="Generate candidate resolution actions for a conflict")
def get_conflict_candidates(conflict_id: str):
    """
    Synthesizes candidate dispatch actions (HOLD, PRIORITIZE, CROSSING_WAIT, SPEED_ADVISORY)
    specifically designed to resolve this conflict.
    """
    conflicts = conflict_detector.detect_all()
    match = next((c for c in conflicts if c.conflict_id == conflict_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Conflict '{conflict_id}' not found.")

    candidates = action_generator.generate_actions_for_conflict(match)

    return {
        "success": True,
        "data": {
            "conflict_id": conflict_id,
            "conflict": match.to_dict(),
            "candidates": [a.to_dict() for a in candidates],
            "total_candidates": len(candidates),
            "feasible_count": sum(1 for a in candidates if a.is_feasible),
        },
        "error": None,
    }
