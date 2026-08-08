from fastapi import APIRouter
from pydantic import BaseModel

from ..services.twin.scenario_loader import scenario_loader, ScenarioLoadError
from ..services.twin.digital_twin import digital_twin
from ..services.twin.network_graph import rail_network
from ..simulation.engine import simulation_engine

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


class LoadScenarioBody(BaseModel):
    scenario_id: str


@router.get("")
def list_scenarios():
    scenarios = scenario_loader.list_scenarios()
    return {"success": True, "data": {"scenarios": scenarios, "total": len(scenarios)}, "error": None}


@router.post("/load")
def load_scenario(body: LoadScenarioBody):
    try:
        scenario = scenario_loader.load(body.scenario_id, rail_network)
        timetable = scenario_loader.compute_timetable(scenario, rail_network)

        # Load into Digital Twin
        digital_twin.load_scenario(scenario, timetable)

        # Load into Simulation Engine (BASELINE strategy by default)
        simulation_engine.load_scenario(scenario, rail_network, timetable)

        return {
            "success": True,
            "data": {
                "scenario_id": scenario["scenario_id"],
                "name": scenario["name"],
                "train_count": len(scenario["trains"]),
                "message": f"Scenario '{scenario['name']}' loaded successfully.",
            },
            "error": None,
        }
    except ScenarioLoadError as e:
        return {"success": False, "data": None,
                "error": {"code": e.code, "message": e.message}}
    except Exception as e:
        return {"success": False, "data": None,
                "error": {"code": "LOAD_FAILED", "message": str(e)}}


@router.post("/reset")
def reset_scenario():
    simulation_engine.reset()
    digital_twin.reset()
    return {"success": True, "data": {"message": "Scenario reset. System is idle."}, "error": None}
