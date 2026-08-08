from fastapi import APIRouter
from ..services.twin.network_graph import rail_network

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("")
def get_network():
    if not rail_network.is_loaded():
        return {"success": False, "data": None,
                "error": {"code": "NETWORK_NOT_LOADED", "message": "Network not initialised."}}
    return {
        "success": True,
        "data": {
            "nodes": rail_network.get_all_nodes(),
            "sections": rail_network.get_all_sections(),
            "routes": rail_network.get_all_routes(),
        },
        "error": None,
    }
