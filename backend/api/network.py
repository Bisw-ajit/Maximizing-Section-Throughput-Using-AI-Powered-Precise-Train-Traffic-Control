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


@router.get("/sidings", summary="Get station loop line and siding capacity status (RAIL-16)")
def get_station_sidings():
    """
    Returns real-time and nominal loop/siding capacity headroom and utilization
    across the entire corridor (KUR, BBS, CTK, PURI, SIL, etc.) to evaluate bottleneck risks.
    """
    from ..services.optimization.siding_optimizer import siding_optimizer

    all_sidings = siding_optimizer.get_all_siding_status()
    return {
        "success": True,
        "data": {
            "sidings": {k: v.to_dict() for k, v in all_sidings.items()},
            "total_stations_monitored": len(all_sidings),
            "congested_stations": [k for k, v in all_sidings.items() if v.is_congested],
            "saturated_stations": [k for k, v in all_sidings.items() if v.is_saturated],
        },
        "error": None,
    }
