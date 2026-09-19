"""
RAILOPTIX — Analytics & Historical KPI Aggregation API (RAIL-14)
================================================================
Endpoints:
  GET    /api/analytics/compare -> Retrieve side-by-side Baseline vs AI-Assisted comparison
  GET    /api/analytics/runs    -> List historical simulation runs from database
  GET    /api/analytics/summary -> Lifetime & scenario macro KPI benchmarks (minutes saved, protection rate)
  POST   /api/analytics/save    -> Record a simulation run into database
  DELETE /api/analytics/history -> Clear run history cache
"""

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from ..simulation.dual_runner import dual_simulator
from ..services.analytics.kpi_aggregator import kpi_aggregator
from ..services.analytics.report_exporter import report_exporter
from ..services.analytics.audit_logger import audit_logger

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class SaveRunRequest(BaseModel):
    run_id: Optional[str] = None
    scenario_id: str = "scenario_001"
    strategy: str = "BASELINE"
    throughput: int = 5
    average_delay: float = 12.0
    p1_delay: float = 10.0
    waiting_time: float = 30.0
    conflict_count: int = 2
    utilization: float = 1.0


@router.get("/compare", summary="Compare Baseline vs AI-Assisted simulation KPIs")
def compare_runs(scenario_id: Optional[str] = "scenario_001"):
    """
    Returns comparative analytics between Baseline (FCFS) and AI-Assisted dispatch.
    If no comparison run has been executed yet, runs on the fly and returns the results.
    """
    latest = dual_simulator.get_latest_comparison()
    if not latest or latest.get("scenario_id") != scenario_id:
        from ..services.twin.scenario_loader import scenario_loader
        from ..services.twin.network_graph import rail_network
        scenario = scenario_loader.load(scenario_id or "scenario_001", rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)
        latest = dual_simulator.compare_strategies(scenario, rail_network, timetable)

    return {
        "success": True,
        "data": latest,
        "error": None,
    }


@router.get("/runs", summary="List historical simulation runs")
async def list_runs(
    limit: int = Query(50, ge=1, le=200),
    scenario_id: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
):
    """Retrieve historical simulation runs stored in the database with optional filters."""
    runs = await kpi_aggregator.get_runs(limit=limit, scenario_id=scenario_id, strategy=strategy)
    return {
        "success": True,
        "data": {"runs": runs, "total": len(runs)},
        "error": None,
    }


@router.get("/summary", summary="Get aggregated lifetime & scenario KPI benchmarks")
def get_kpi_summary(scenario_id: Optional[str] = Query(None)):
    """
    Computes macro corridor KPIs across all historical simulation runs:
    cumulative delay saved, P1 protection rate, and conflict resolution rate.
    """
    summary = kpi_aggregator.get_summary(scenario_id=scenario_id)
    return {
        "success": True,
        "data": summary,
        "error": None,
    }


@router.post("/save", summary="Record a simulation run into database")
async def save_run(body: SaveRunRequest):
    """Explicitly save a simulation run result into the persistent database."""
    record = await kpi_aggregator.save_run(body.model_dump())
    return {
        "success": True,
        "data": record,
        "message": f"Run '{record['run_id']}' recorded successfully.",
        "error": None,
    }


@router.delete("/history", summary="Clear run cache")
def clear_history():
    kpi_aggregator.clear_cache()
    return {"success": True, "message": "Simulation run history cache cleared.", "error": None}


# ── RAIL-18: Export & Audit Log Endpoints ────────────────────────────────────

@router.get("/export/csv", summary="Export simulation metrics & train traces to CSV (RAIL-18)")
def export_csv(scenario_id: str = "scenario_001"):
    """Generates and streams an RFC 4180 CSV export of the simulation run."""
    csv_content = report_exporter.generate_csv_report(scenario_id=scenario_id)
    filename = f"railoptix_simulation_{scenario_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/report", summary="Generate printable HTML/PDF executive report (RAIL-18)")
def export_html_report(scenario_id: str = "scenario_001"):
    """Generates an executive HTML report formatted for browser Print-to-PDF."""
    html_content = report_exporter.generate_html_pdf_report(scenario_id=scenario_id)
    return Response(content=html_content, media_type="text/html")


@router.get("/audit-log", summary="Retrieve chronological dispatch audit trail (RAIL-18)")
def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None),
    train_id: Optional[str] = Query(None),
):
    """Returns sequential audit trail of train movements, signal transitions, and controller interventions."""
    entries = audit_logger.get_entries(limit=limit, category=category, train_id=train_id)
    return {
        "success": True,
        "data": {
            "entries": entries,
            "total_returned": len(entries),
        },
        "error": None,
    }
