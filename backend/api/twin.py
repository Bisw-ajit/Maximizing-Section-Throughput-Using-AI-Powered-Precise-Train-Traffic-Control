from fastapi import APIRouter
from datetime import datetime

from ..services.twin.digital_twin import digital_twin
from ..providers.railradar.adapter import RailRadarAdapter, ScenarioFallbackAdapter
from ..core.config import settings

router = APIRouter(prefix="/api/twin", tags=["digital-twin"])

_live_adapter = RailRadarAdapter(api_key=settings.RAILRADAR_API_KEY)
_fallback_adapter = ScenarioFallbackAdapter(twin=digital_twin)


@router.post("/sync")
async def sync_twin():
    """Push latest train data (live or fallback) into the Digital Twin."""
    try:
        adapter = _live_adapter if settings.RAILRADAR_API_KEY else _fallback_adapter
        records = await adapter.fetch_trains()
        digital_twin.update_from_live(records)
        return {
            "success": True,
            "data": {"synced": len(records), "synced_at": datetime.utcnow().isoformat()},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None,
                "error": {"code": "SYNC_FAILED", "message": str(e)}}


@router.get("/state")
def get_twin_state():
    """Return the full current Digital Twin state snapshot."""
    return {"success": True, "data": digital_twin.get_state(), "error": None}
