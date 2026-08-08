import simpy
from datetime import datetime


def train_process(env: simpy.Environment, train: dict, route_sections: list[dict],
                  section_resources: dict, timetable: dict, engine):
    """
    SimPy generator process for a single train moving through its route.

    Each train:
      1. Waits until its scheduled departure (sim-time)
      2. For each section: requests the section resource (blocks if at capacity)
      3. Travels through the section (timeout = travel_time / speed)
      4. Emits events consumed by the Digital Twin
      5. Dwells at each station node
    """
    train_id = train["train_id"]
    avg_speed = train.get("avg_speed_kmh", 70)
    dwell_times: dict[str, int] = train.get("dwell_time_minutes", {})

    # Parse scheduled departure into sim minutes from midnight
    h, m = map(int, train["scheduled_departure"].split(":"))
    scheduled_dep_minutes = h * 60 + m

    # Wait until departure time (env starts at 0 = midnight)
    if env.now < scheduled_dep_minutes:
        yield env.timeout(scheduled_dep_minutes - env.now)

    # Compute initial delay based on actual departure vs scheduled
    actual_dep = env.now
    running_delay = max(0.0, actual_dep - scheduled_dep_minutes)

    route_node_seq = _build_node_sequence(route_sections)

    for i, section in enumerate(route_sections):
        section_id = section["section_id"]
        from_node = section["from_node"]
        to_node = section["to_node"]
        length_km = section.get("length_km", 30)

        resource = section_resources.get(section_id)
        if resource is None:
            # Try reverse section ID
            rev_id = f"{to_node}-{from_node}"
            resource = section_resources.get(rev_id)

        wait_start = env.now

        # Request section access (blocks if at capacity — this is where crossing conflicts happen)
        if resource:
            req = resource.request()
            yield req
        else:
            req = None

        wait_end = env.now
        wait_minutes = wait_end - wait_start

        if wait_minutes > 0.5:
            running_delay += wait_minutes
            engine.emit_event("HELD", train_id, {
                "section_id": section_id,
                "wait_minutes": round(wait_minutes, 2),
            })

        # Enter section
        engine.emit_event("SECTION_ENTER", train_id, {
            "section_id": section_id,
            "from_node": from_node,
            "to_node": to_node,
            "direction": _get_direction(from_node, to_node),
        })

        # Travel time in sim-minutes
        speed = avg_speed * engine.speed_multiplier if engine.speed_multiplier > 0 else avg_speed
        travel_minutes = (length_km / speed) * 60
        yield env.timeout(travel_minutes)

        # Exit section
        engine.emit_event("SECTION_EXIT", train_id, {
            "section_id": section_id,
        })

        if resource and req:
            resource.release(req)

        # Arrive at destination node of this section
        actual_arrival = env.now
        tt_node = timetable.get(to_node, {})
        scheduled_arr = tt_node.get("scheduled_arrival")
        if scheduled_arr:
            scheduled_arr_minutes = _dt_to_sim_minutes(scheduled_arr)
            running_delay = max(0.0, actual_arrival - scheduled_arr_minutes)

        next_station = route_node_seq[i + 2] if i + 2 < len(route_node_seq) else None

        engine.emit_event("ARRIVAL", train_id, {
            "node_id": to_node,
            "delay_minutes": round(running_delay, 2),
            "next_station": next_station,
        })

        # Update journey progress
        progress = (i + 1) / len(route_sections)
        from ..services.twin.digital_twin import digital_twin
        digital_twin.update_train_state(train_id, journey_progress=progress)

        # Dwell at station (not at the very last stop)
        if i < len(route_sections) - 1:
            dwell = dwell_times.get(to_node, 2)
            if dwell > 0:
                yield env.timeout(dwell)

    # Train completed its route
    engine.emit_event("COMPLETED", train_id, {
        "final_delay_minutes": round(running_delay, 2),
    })


def _build_node_sequence(sections: list[dict]) -> list[str]:
    if not sections:
        return []
    nodes = [sections[0]["from_node"]]
    for s in sections:
        nodes.append(s["to_node"])
    return nodes


def _get_direction(from_node: str, to_node: str) -> str:
    # Simple heuristic based on network geography
    southbound = {"CTK", "BBS", "KUR", "PURI", "KLK", "BAM"}
    node_order = ["CTK", "BBS", "KUR", "PURI", "KLK", "BAM"]
    try:
        from_idx = node_order.index(from_node)
        to_idx = node_order.index(to_node)
        return "SOUTHBOUND" if to_idx >= from_idx else "NORTHBOUND"
    except ValueError:
        return "UNKNOWN"


def _dt_to_sim_minutes(dt: datetime) -> float:
    return dt.hour * 60 + dt.minute + dt.second / 60
