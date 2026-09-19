"""
RAILOPTIX — Corridor Network Mapper & Geolocation Resolver
===========================================================
Maps external raw telemetry (station codes, Indian Railways station names,
GPS coordinates) into RAILOPTIX network topological entities (nodes, sections, routes).

Used by: RailRadarAdapter, Live Feeder, and API layer.
"""

import math
from typing import Optional, Tuple
from .network_graph import rail_network

# Station aliases to canonical RAILOPTIX Node IDs
STATION_ALIASES: dict[str, str] = {
    # Cuttack
    "CTK": "CTK", "CUTTACK": "CTK", "CUTTACK JN": "CTK", "CUTTACK JUNCTION": "CTK",
    # Barang
    "BGBR": "BGBR", "BARANG": "BGBR", "BARANG JN": "BGBR",
    # Bhubaneswar
    "BBS": "BBS", "BHUBANESWAR": "BBS", "BHUBANESHWAR": "BBS", "BHUBANESWAR MAIN": "BBS",
    # Retang
    "RET": "RET", "RETANG": "RET",
    # Khurda Road
    "KUR": "KUR", "KHURDA ROAD": "KUR", "KHURDA ROAD JN": "KUR", "KHURDA": "KUR", "KHURDA RD": "KUR",
    # Sakhigopal
    "SIL": "SIL", "SAKHIGOPAL": "SIL", "SAKHI GOPAL": "SIL",
    # Puri
    "PURI": "PURI", "PURI TERMINUS": "PURI", "JAGANNATH PURI": "PURI",
    # Balugaon
    "BALU": "BALU", "BALUGAON": "BALU",
    # Khallikote
    "KLK": "KLK", "KHALLIKOTE": "KLK", "KHALIKOTE": "KLK",
    # Chatrapur
    "CAP": "CAP", "CHATRAPUR": "CAP", "CHHATRAPUR": "CAP",
    # Brahmapur
    "BAM": "BAM", "BRAHMAPUR": "BAM", "BERHAMPUR": "BAM",
}


def canonical_station(raw_code: Optional[str]) -> Optional[str]:
    """Map any station code/name variant to the canonical corridor node_id."""
    if not raw_code:
        return None
    cleaned = str(raw_code).strip().upper()
    return STATION_ALIASES.get(cleaned, cleaned if cleaned in rail_network.nodes else None)


def nearest_corridor_node(lat: float, lon: float, max_dist_km: float = 35.0) -> Optional[str]:
    """
    Find the closest RAILOPTIX station node to a GPS coordinate.
    Uses Haversine distance formula.
    """
    nodes = rail_network.get_all_nodes()
    if not nodes:
        return None

    best_node = None
    min_dist = float("inf")

    for node in nodes:
        n_lat = node.get("latitude")
        n_lon = node.get("longitude")
        if n_lat is None or n_lon is None:
            continue

        # Haversine distance calculation
        dlat = math.radians(n_lat - lat)
        dlon = math.radians(n_lon - lon)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat)) * math.cos(math.radians(n_lat)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_km = 6371.0 * c

        if dist_km < min_dist:
            min_dist = dist_km
            best_node = node["node_id"]

    return best_node if min_dist <= max_dist_km else None


def deduce_route_and_direction(
    origin_node: Optional[str],
    current_node: Optional[str],
    destination_node: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Determine route_id ('route_A', 'route_B', etc.) and direction ('SOUTHBOUND' / 'NORTHBOUND').
    """
    curr = canonical_station(current_node)
    dest = canonical_station(destination_node)
    orig = canonical_station(origin_node)

    # If destination is Puri
    if dest == "PURI" or (orig in ("CTK", "BBS") and curr in ("SIL", "PURI")):
        return "route_A", "SOUTHBOUND"
    # If destination is Brahmapur
    if dest == "BAM" or (orig in ("CTK", "BBS") and curr in ("BALU", "KLK", "CAP", "BAM")):
        return "route_B", "SOUTHBOUND"
    # If coming from Puri towards Cuttack/Bhubaneswar
    if orig == "PURI" or dest in ("CTK", "BBS") and curr in ("SIL", "KUR", "RET"):
        return "route_C", "NORTHBOUND"
    # If coming from Brahmapur towards Cuttack/Bhubaneswar
    if orig == "BAM" or dest in ("CTK", "BBS") and curr in ("CAP", "KLK", "BALU"):
        return "route_D", "NORTHBOUND"

    # Default fallback heuristics
    southbound_seq = ["CTK", "BGBR", "BBS", "RET", "KUR", "SIL", "PURI"]
    if curr in southbound_seq:
        return "route_A", "SOUTHBOUND"

    return "route_A", "SOUTHBOUND"


def deduce_section(from_node: Optional[str], to_node: Optional[str]) -> Optional[str]:
    """Find direct or intermediate section between two stations."""
    fn = canonical_station(from_node)
    tn = canonical_station(to_node)
    if not fn:
        return None

    # Direct edge in graph
    if tn:
        sec_id = rail_network.get_section_id(fn, tn)
        if sec_id:
            return sec_id

    # Fallback to outgoing section from fn
    neighbors = rail_network.get_neighbors(fn)
    if neighbors:
        return rail_network.get_section_id(fn, neighbors[0])

    return None


def calculate_journey_progress(
    route_id: Optional[str],
    current_node: Optional[str],
) -> float:
    """Calculate normalized journey progress (0.0 to 1.0) along route."""
    if not route_id or not current_node:
        return 0.0

    route = rail_network.get_route(route_id)
    if not route:
        return 0.0

    nodes = route.get("node_sequence", [])
    curr = canonical_station(current_node)
    if not curr or curr not in nodes:
        return 0.0

    idx = nodes.index(curr)
    total = max(len(nodes) - 1, 1)
    return round(idx / total, 3)
