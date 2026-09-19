"""
RAILOPTIX — Simulation API Router (Dual-Mode Simulation Support)
================================================================
Endpoints:
  POST /api/simulation/start       -> Start real-time simulation
  POST /api/simulation/pause       -> Pause simulation
  POST /api/simulation/resume      -> Resume simulation
  POST /api/simulation/reset       -> Reset simulation
  POST /api/simulation/speed       -> Adjust speed multiplier (0.25x - 20x)
  POST /api/simulation/strategy    -> Toggle strategy (BASELINE vs AI_ASSISTED)
  POST /api/simulation/compare     -> Run headless fast-forward dual-mode comparison
  GET  /api/simulation/status      -> Simulation clock and train status
  GET  /api/simulation/kpis        -> Current run KPIs
  GET  /api/simulation/events      -> Stream of recent simulation events
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..simulation.engine import simulation_engine, SimulationStatus, SimulationStrategy
from ..simulation.dual_runner import dual_simulator

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


class SpeedBody(BaseModel):
    multiplier: float = 1.0


class StrategyBody(BaseModel):
    strategy: str  # "BASELINE" or "AI_ASSISTED"


class CompareBody(BaseModel):
    scenario_id: Optional[str] = "scenario_001"


class StressTestBody(BaseModel):
    scenario_id: Optional[str] = "scenario_003"
    additional_delay_minutes: float = 0.0
    enforce_siding_limits: bool = True


@router.post("/start", summary="Start or resume simulation")
def start_simulation():
    try:
        if not simulation_engine.scenario:
            from ..services.twin.scenario_loader import scenario_loader
            from ..services.twin.digital_twin import digital_twin
            from ..services.twin.network_graph import rail_network
            scenario = scenario_loader.load("scenario_001", rail_network)
            timetable = scenario_loader.compute_timetable(scenario, rail_network)
            digital_twin.load_scenario(scenario, timetable)
            simulation_engine.load_scenario(scenario, rail_network, timetable, simulation_engine.strategy)
        simulation_engine.start()
        return {
            "success": True,
            "data": {
                "message": f"Simulation started ({simulation_engine.strategy.value}).",
                "status": simulation_engine.status.value,
                "strategy": simulation_engine.strategy.value,
            },
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "error": {"code": "START_FAILED", "message": str(e)}}


@router.post("/pause", summary="Pause live simulation")
def pause_simulation():
    simulation_engine.pause()
    return {
        "success": True,
        "data": {"message": "Simulation paused.", "status": simulation_engine.status.value},
        "error": None,
    }


@router.post("/resume", summary="Resume live simulation")
def resume_simulation():
    simulation_engine.resume()
    return {
        "success": True,
        "data": {"message": "Simulation resumed.", "status": simulation_engine.status.value},
        "error": None,
    }


@router.post("/reset", summary="Reset simulation clock")
def reset_simulation():
    simulation_engine.reset()
    return {"success": True, "data": {"message": "Simulation reset. System is idle."}, "error": None}


@router.post("/speed", summary="Set clock speed multiplier")
def set_speed(body: SpeedBody):
    simulation_engine.set_speed(body.multiplier)
    return {"success": True, "data": {"speed_multiplier": simulation_engine.speed_multiplier}, "error": None}


@router.post("/strategy", summary="Toggle dispatch strategy (BASELINE vs AI_ASSISTED)")
def set_strategy(body: StrategyBody):
    try:
        strat = SimulationStrategy(body.strategy.upper())
        simulation_engine.set_strategy(strat)
        return {
            "success": True,
            "data": {
                "strategy": strat.value,
                "message": f"Dispatch policy switched to {strat.value}.",
            },
            "error": None,
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy '{body.strategy}'. Must be 'BASELINE' or 'AI_ASSISTED'.",
        )


@router.post("/compare", summary="Run dual-mode fast-forward comparison (Baseline vs AI-Assisted)")
def compare_simulation(body: Optional[CompareBody] = None):
    """
    Executes headless simulation of the scenario under both BASELINE and AI_ASSISTED
    policies, computing side-by-side KPI comparison in milliseconds.
    """
    scen_id = body.scenario_id if body and body.scenario_id else "scenario_001"
    try:
        from ..services.twin.scenario_loader import scenario_loader
        from ..services.twin.network_graph import rail_network
        scenario = scenario_loader.load(scen_id, rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)

        comparison = dual_simulator.compare_strategies(scenario, rail_network, timetable)
        return {"success": True, "data": comparison, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": {"code": "COMPARE_FAILED", "message": str(e)}}


@router.post("/stress-test", summary="Execute multi-train saturation edge-case stress test (RAIL-16)")
def run_stress_test(body: Optional[StressTestBody] = None):
    """
    Simulates high-density saturation test (10 simultaneous trains under extreme delay
    and speed restrictions). Evaluates siding capacity limits and secondary deadlock prevention.
    """
    scen_id = body.scenario_id if body and body.scenario_id else "scenario_003"
    add_del = body.additional_delay_minutes if body else 0.0
    siding_lim = body.enforce_siding_limits if body is not None else True

    try:
        from ..simulation.stress_runner import stress_test_runner
        result = stress_test_runner.run_stress_test(
            scenario_id=scen_id,
            additional_delay_minutes=add_del,
            enforce_siding_limits=siding_lim,
        )
        return {"success": True, "data": result.to_dict(), "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": {"code": "STRESS_TEST_FAILED", "message": str(e)}}


@router.get("/status", summary="Get current clock and run state")
def get_status():
    st = simulation_engine.get_status()
    st["strategy"] = simulation_engine.strategy.value
    return {"success": True, "data": st, "error": None}


@router.get("/kpis", summary="Get current run KPIs")
def get_kpis():
    return {"success": True, "data": simulation_engine.get_kpis(), "error": None}


@router.get("/events", summary="Get recent simulation events")
def get_events(limit: int = 50):
    events = simulation_engine.events[-limit:]
    return {"success": True, "data": {"events": events, "total": len(simulation_engine.events)}, "error": None}
