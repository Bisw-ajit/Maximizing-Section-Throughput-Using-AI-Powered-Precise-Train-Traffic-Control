"""
RAILOPTIX — Multi-Objective AI Decision & Recommendations API
==============================================================
Endpoints:
  POST /api/recommendations         -> Generate & multi-objective score recommendations
  GET  /api/recommendations         -> Get current recommendations (balanced profile)
  POST /api/recommendations/apply   -> Execute / apply a recommendation to Digital Twin
  GET  /api/recommendations/history -> Audit log of applied dispatch actions
  GET  /api/recommendations/profiles -> Multi-objective weight presets
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..services.decision.engine import decision_engine
from ..services.decision.evaluator import PRESET_PROFILES

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class RecommendationRequest(BaseModel):
    conflict_id: Optional[str] = None
    profile: Optional[str] = "BALANCED"  # BALANCED, PRIORITY_FIRST, THROUGHPUT_MAX, DELAY_MIN
    weights: Optional[Dict[str, float]] = None


class ApplyRecommendationRequest(BaseModel):
    action_id: str


@router.post("", summary="Multi-objective evaluation and recommendation generation")
def generate_recommendations(body: Optional[RecommendationRequest] = None):
    """
    Evaluates candidate actions using Pareto multi-attribute utility scoring:
    combining Priority Preservation, Delay Minimization, Wait-Time Relief,
    Throughput Maximization, and Single-Line Congestion Relief.
    """
    conflict_id = body.conflict_id if body else None
    profile = body.profile if body else "BALANCED"
    weights = body.weights if body else None

    try:
        result = decision_engine.evaluate_and_recommend(
            conflict_id=conflict_id,
            profile=profile,
            custom_weights=weights,
        )
        return {
            "success": True,
            "data": result,
            "error": None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {"code": "EVALUATION_FAILED", "message": str(e)},
        }


@router.get("", summary="List current evaluated recommendations")
def get_recommendations():
    """Retrieve current evaluated recommendations under default balanced profile."""
    return generate_recommendations(None)


@router.post("/apply", summary="Execute a recommendation on the Digital Twin")
def apply_recommendation(body: ApplyRecommendationRequest):
    """
    Applies the specified candidate action directly to the Digital Twin.
    Updates train status (e.g. HELD, PRIORITIZED, SPEED_RESTRICTED),
    enforces siding loop diversions, and appends to the immutable dispatch audit log.
    """
    try:
        res = decision_engine.apply_action(body.action_id)
        return {
            "success": True,
            "data": res,
            "error": None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {"code": "ACTION_APPLICATION_FAILED", "message": str(e)},
        }


@router.get("/history", summary="Audit log of applied dispatch actions")
def get_applied_history():
    """Returns chronologically ordered audit trail of all actions executed during this session."""
    history = decision_engine.get_applied_history()
    return {
        "success": True,
        "data": {
            "history": history,
            "total_applied": len(history),
        },
        "error": None,
    }


@router.get("/profiles", summary="List multi-objective weight presets")
def get_profiles():
    """Returns available objective weight configurations (Balanced, Priority-First, Throughput-Max, Delay-Min)."""
    profiles_data = {}
    for p_enum, w in PRESET_PROFILES.items():
        profiles_data[p_enum.value] = {
            "priority_weight": w.priority_weight,
            "delay_weight": w.delay_weight,
            "wait_time_weight": w.wait_time_weight,
            "throughput_weight": w.throughput_weight,
            "congestion_weight": w.congestion_weight,
        }

    return {
        "success": True,
        "data": {
            "profiles": profiles_data,
            "default_profile": "BALANCED",
        },
        "error": None,
    }


@router.get("/{recommendation_id}/explain", summary="Explain AI dispatch decision rationale (XAI)")
def explain_recommendation(recommendation_id: str):
    """
    Synthesizes a multi-tier Explainable AI (XAI) rationale for this recommendation:
    executive summary, driving factors with percentage attributions,
    counterfactual alternative analysis, and Indian Railways regulatory rule citations.
    """
    from ..services.conflict.conflict_detector import conflict_detector
    from ..services.decision.action_generator import action_generator
    from ..services.decision.evaluator import multi_objective_evaluator
    from ..services.decision.explainer import xai_explainer

    all_conflicts = conflict_detector.detect_all()
    all_cands = []
    for conf in all_conflicts:
        cands = action_generator.generate_actions_for_conflict(conf)
        all_cands.extend(cands)

    evaluated = multi_objective_evaluator.evaluate_candidates(all_cands)
    target = next((e for e in evaluated if e.action.action_id == recommendation_id), None)

    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation '{recommendation_id}' not found in active candidate actions."
        )

    explanation = xai_explainer.explain_action(target, evaluated)
    return {
        "success": True,
        "data": explanation.to_dict(),
        "error": None,
    }

