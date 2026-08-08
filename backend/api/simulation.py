from fastapi import APIRouter
from pydantic import BaseModel
from ..simulation.engine import simulation_engine, SimulationStatus

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


class SpeedBody(BaseModel):
    multiplier: float = 1.0


@router.post("/start")
def start_simulation():
    try:
        simulation_engine.start()
        return {"success": True, "data": {"message": "Simulation started.",
                "status": simulation_engine.status.value}, "error": None}
    except RuntimeError as e:
        return {"success": False, "data": None,
                "error": {"code": "START_FAILED", "message": str(e)}}


@router.post("/pause")
def pause_simulation():
    simulation_engine.pause()
    return {"success": True, "data": {"message": "Simulation paused.",
            "status": simulation_engine.status.value}, "error": None}


@router.post("/resume")
def resume_simulation():
    simulation_engine.resume()
    return {"success": True, "data": {"message": "Simulation resumed.",
            "status": simulation_engine.status.value}, "error": None}


@router.post("/reset")
def reset_simulation():
    simulation_engine.reset()
    return {"success": True, "data": {"message": "Simulation reset. System is idle."}, "error": None}


@router.post("/speed")
def set_speed(body: SpeedBody):
    simulation_engine.set_speed(body.multiplier)
    return {"success": True, "data": {"speed_multiplier": simulation_engine.speed_multiplier}, "error": None}


@router.get("/status")
def get_status():
    return {"success": True, "data": simulation_engine.get_status(), "error": None}


@router.get("/kpis")
def get_kpis():
    return {"success": True, "data": simulation_engine.get_kpis(), "error": None}


@router.get("/events")
def get_events(limit: int = 50):
    events = simulation_engine.events[-limit:]
    return {"success": True, "data": {"events": events, "total": len(simulation_engine.events)}, "error": None}
