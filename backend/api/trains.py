from fastapi import APIRouter
from datetime import datetime

from ..services.twin.digital_twin import digital_twin
from ..services.twin.network_graph import rail_network
from ..providers.railradar.adapter import RailRadarAdapter, ScenarioFallbackAdapter
from ..core.config import settings

router = APIRouter(prefix="/api/trains", tags=["trains"])

# Use live adapter if key present, else fallback
_live_adapter = RailRadarAdapter(api_key=settings.RAILRADAR_API_KEY)
_fallback_adapter = ScenarioFallbackAdapter(twin=digital_twin)


def _get_adapter():
    return _live_adapter if settings.RAILRADAR_API_KEY else _fallback_adapter


@router.get("/live")
async def get_live_trains():
    try:
        adapter = _get_adapter()
        records = await adapter.fetch_trains()
        # Update digital twin with the records
        digital_twin.update_from_live(records)
        return {
            "success": True,
            "data": {
                "trains": records,
                "total": len(records),
                "last_updated": datetime.utcnow().isoformat(),
                "source": "railradar" if settings.RAILRADAR_API_KEY else "scenario_fallback",
                "is_live": bool(settings.RAILRADAR_API_KEY),
            },
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None,
                "error": {"code": "FETCH_FAILED", "message": str(e)}}


@router.get("/{train_id}")
def get_train_detail(train_id: str):
    train = digital_twin.get_train(train_id)
    if not train:
        return {"success": False, "data": None,
                "error": {"code": "TRAIN_NOT_FOUND",
                          "message": f"Train '{train_id}' not found in Digital Twin."}}
    node = rail_network.get_node(train.current_node) if train.current_node else None
    return {
        "success": True,
        "data": {
            "train_id": train.train_id,
            "train_number": train.train_number,
            "name": train.name,
            "priority": train.priority,
            "current_node": train.current_node,
            "current_node_name": node["name"] if node else None,
            "current_section": train.current_section,
            "direction": train.direction,
            "status": train.status,
            "delay_minutes": train.delay_minutes,
            "next_station": train.next_station,
            "route_id": train.route_id,
            "last_updated": train.last_updated.isoformat(),
            "data_source": train.data_source.value,
            "is_live": train.is_live,
            "staleness_seconds": train.staleness_seconds,
            "journey_progress": train.journey_progress,
        },
        "error": None,
    }
