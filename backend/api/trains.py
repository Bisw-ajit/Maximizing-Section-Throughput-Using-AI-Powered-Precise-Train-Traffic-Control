"""
RAILOPTIX — Trains & Live Telemetry API
========================================
Endpoints:
  GET  /api/trains/live              -> Fetch live normalized train telemetry
  POST /api/trains/live/sync         -> Force sync live telemetry into Digital Twin
  GET  /api/trains/live/provider-status -> Diagnostic info on upstream API & cache
  GET  /api/trains                   -> List all current corridor trains
  GET  /api/trains/{train_id}        -> Detailed inspection of a specific train
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional, List

from ..services.twin.digital_twin import digital_twin
from ..services.twin.network_graph import rail_network
from ..providers.railradar.adapter import (
    RailRadarAdapter,
    ScenarioFallbackAdapter,
    RealisticCorridorFeeder,
)
from ..core.config import settings

router = APIRouter(prefix="/api/trains", tags=["trains"])

# Initialize adapters
_live_adapter = RailRadarAdapter(
    api_key=settings.RAILRADAR_API_KEY,
    base_url=settings.RAILRADAR_BASE_URL,
    enable_mock_fallback=settings.RAILRADAR_MOCK_FALLBACK,
)
_mock_feeder = RealisticCorridorFeeder()
_scenario_adapter = ScenarioFallbackAdapter(twin=digital_twin)


def _resolve_adapter(mode: str):
    """Select the appropriate provider adapter according to requested mode."""
    mode_clean = mode.lower().strip()
    if mode_clean == "scenario":
        return _scenario_adapter
    elif mode_clean == "mock":
        return _mock_feeder
    elif mode_clean == "live":
        return _live_adapter
    else:  # "auto"
        # If API key configured or fallback enabled, use live adapter
        if settings.RAILRADAR_API_KEY or settings.RAILRADAR_MOCK_FALLBACK:
            return _live_adapter
        return _scenario_adapter


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/live", summary="Fetch live corridor train telemetry")
async def get_live_trains(
    force_refresh: bool = Query(False, description="Bypass in-memory cache and refetch from upstream"),
    mode: str = Query("auto", description="Provider mode: 'auto', 'live', 'mock', 'scenario'"),
    train_number: Optional[str] = Query(None, description="Filter for a specific train number"),
):
    """
    Ingests live train records from the RailRadar adapter or realistic corridor feed,
    normalizes them to the RAILOPTIX topological network, and automatically synchronizes
    with the in-memory Digital Twin state.
    """
    try:
        adapter = _resolve_adapter(mode)
        filter_nums = [train_number] if train_number else None

        records = await adapter.fetch_trains(
            train_numbers=filter_nums,
            force_refresh=force_refresh,
        )

        # Merge live records into Digital Twin state
        sync_stats = digital_twin.update_from_live(records)

        return {
            "success": True,
            "data": {
                "trains": records,
                "total": len(records),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "source": getattr(adapter, "active_source", type(adapter).__name__),
                "is_live": True if mode in ("auto", "live", "mock") else False,
                "cache_age_seconds": getattr(adapter, "cache_age_seconds", 0.0),
                "digital_twin_sync": sync_stats,
            },
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {"code": "FETCH_FAILED", "message": str(e)},
        }


@router.post("/live/sync", summary="Force synchronize live telemetry into Digital Twin")
async def sync_live_telemetry():
    """
    Explicitly forces a fresh poll from the live provider and pushes all
    train positions and section occupancies into the Digital Twin.
    """
    try:
        adapter = _resolve_adapter("auto")
        records = await adapter.fetch_trains(force_refresh=True)
        sync_stats = digital_twin.update_from_live(records)

        return {
            "success": True,
            "data": {
                "message": "Digital Twin synchronized with live corridor telemetry.",
                "sync_stats": sync_stats,
                "active_trains_count": len(digital_twin.get_all_trains()),
                "section_occupancy": digital_twin.get_section_occupancy(),
                "synced_at": datetime.now(timezone.utc).isoformat(),
            },
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {"code": "SYNC_FAILED", "message": str(e)},
        }


@router.get("/live/provider-status", summary="Check upstream live data provider configuration")
def get_provider_status():
    """
    Returns diagnostics on the RailRadar adapter, caching metrics,
    and active fallback configurations.
    """
    key = settings.RAILRADAR_API_KEY
    masked_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else ("CONFIGURED" if key else "NOT_CONFIGURED")

    return {
        "success": True,
        "data": {
            "provider": "RailRadar",
            "base_url": settings.RAILRADAR_BASE_URL,
            "api_key_status": masked_key,
            "mock_fallback_enabled": settings.RAILRADAR_MOCK_FALLBACK,
            "cache_ttl_seconds": _live_adapter.CACHE_TTL_SECONDS,
            "cache_age_seconds": _live_adapter.cache_age_seconds,
            "is_cache_valid": _live_adapter.is_cache_valid,
            "last_fetch_source": _live_adapter.active_source,
            "corridor_monitored": "Cuttack – Bhubaneswar – Khurda Road – Puri / Brahmapur",
        },
        "error": None,
    }


@router.get("", summary="List all active trains in Digital Twin")
def list_trains():
    """Returns all trains currently active within the Digital Twin."""
    trains = digital_twin.get_all_trains()
    results = []
    for t in trains:
        node = rail_network.get_node(t.current_node) if t.current_node else None
        results.append({
            "train_id": t.train_id,
            "train_number": t.train_number,
            "name": t.name,
            "priority": t.priority,
            "current_node": t.current_node,
            "current_node_name": node["name"] if node else None,
            "current_section": t.current_section,
            "direction": t.direction,
            "status": t.status,
            "delay_minutes": t.delay_minutes,
            "next_station": t.next_station,
            "route_id": t.route_id,
            "is_live": t.is_live,
            "data_source": t.data_source.value,
            "staleness_seconds": t.staleness_seconds,
            "journey_progress": t.journey_progress,
        })

    return {
        "success": True,
        "data": {
            "trains": results,
            "count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "error": None,
    }


@router.get("/{train_id}", summary="Detailed inspection of a specific train")
def get_train_detail(train_id: str):
    """Inspect complete telemetry attributes of an individual train."""
    train = digital_twin.get_train(train_id)
    if not train:
        # Check by train_number as fallback
        for t in digital_twin.get_all_trains():
            if t.train_number == train_id:
                train = t
                break

    if not train:
        raise HTTPException(status_code=404, detail=f"Train '{train_id}' not found in Digital Twin.")

    node = rail_network.get_node(train.current_node) if train.current_node else None
    next_node = rail_network.get_node(train.next_station) if train.next_station else None

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
            "next_station_name": next_node["name"] if next_node else None,
            "route_id": train.route_id,
            "last_updated": train.last_updated.isoformat(),
            "data_source": train.data_source.value,
            "is_live": train.is_live,
            "staleness_seconds": train.staleness_seconds,
            "journey_progress": train.journey_progress,
        },
        "error": None,
    }
