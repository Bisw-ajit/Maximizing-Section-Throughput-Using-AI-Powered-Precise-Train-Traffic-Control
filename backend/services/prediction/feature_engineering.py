"""
RAILOPTIX — Feature Engineering
================================
Converts live Digital Twin TrainState + Network info into
feature vectors that match what the XGBoost models were trained on.

Used by: delay_predictor.py
"""

from datetime import datetime, timezone
from typing import Optional
from ...services.twin.digital_twin import TrainState
from ...services.twin.network_graph import rail_network


# ── Peak Hour Definition (matches training data generator) ───────────────────
PEAK_MINUTES: set[int] = set(
    list(range(6 * 60, 10 * 60)) +   # 6:00 AM – 10:00 AM
    list(range(17 * 60, 21 * 60))    # 5:00 PM  – 9:00 PM
)


def _time_of_day_minutes(dt: Optional[datetime] = None) -> int:
    """Return current time as minutes since midnight (0–1439)."""
    now = dt or datetime.now(timezone.utc)
    return now.hour * 60 + now.minute


def _is_peak(time_of_day_min: int) -> int:
    return int(time_of_day_min in PEAK_MINUTES)


def _get_section_info(section_id: Optional[str]) -> dict:
    """Fetch section metadata from the loaded network graph."""
    defaults = {
        "section_length_km": 15.0,
        "section_capacity": 1,
        "is_single_track": 1,
        "speed_limit_kmh": 80.0,
    }
    if not section_id:
        return defaults
    sec = rail_network.sections.get(section_id)
    if not sec:
        return defaults
    return {
        "section_length_km": float(sec.get("length_km", 15.0)),
        "section_capacity":  int(sec.get("capacity", 1)),
        "is_single_track":   int(sec.get("capacity", 1) <= 1),
        "speed_limit_kmh":   float(sec.get("speed_limit_kmh", 80.0)),
    }


def _count_occupancy(section_id: Optional[str], occupancy_map: dict[str, list[str]]) -> int:
    """Number of trains currently in the section."""
    if not section_id:
        return 0
    return len(occupancy_map.get(section_id, []))


def _count_trains_ahead(train: TrainState, all_trains: list[TrainState]) -> int:
    """
    Count how many trains on the SAME route are ahead (further along journey).
    Simple heuristic: same route_id and higher journey_progress.
    """
    if not train.route_id:
        return 0
    return sum(
        1 for t in all_trains
        if t.train_id != train.train_id
        and t.route_id == train.route_id
        and t.journey_progress > train.journey_progress
    )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def build_delay_features(
    train: TrainState,
    all_trains: list[TrainState],
    occupancy_map: dict[str, list[str]],
) -> dict[str, float]:
    """
    Build a feature dict for the delay regression model.
    Column order MUST match DELAY_FEATURES in train_xgboost.py.
    """
    section_info = _get_section_info(train.current_section)
    tod          = _time_of_day_minutes()
    occ          = _count_occupancy(train.current_section, occupancy_map)
    cap          = section_info["section_capacity"]
    trains_ahead = _count_trains_ahead(train, all_trains)

    # Scheduled vs actual diff — use current delay as proxy if timetable unavailable
    sched_vs_actual = train.delay_minutes * 1.0

    # Estimated speed — use section speed limit as proxy (simulation may override)
    speed_kmh = section_info["speed_limit_kmh"] * 0.85  # typical operational factor

    return {
        "current_delay_min":    max(0.0, train.delay_minutes),
        "section_length_km":    section_info["section_length_km"],
        "section_capacity":     float(cap),
        "section_occupancy":    float(occ),
        "is_single_track":      float(section_info["is_single_track"]),
        "train_priority":       float(train.priority),
        "speed_kmh":            speed_kmh,
        "time_of_day_min":      float(tod),
        "is_peak_hour":         float(_is_peak(tod)),
        "trains_ahead":         float(trains_ahead),
        "journey_progress":     float(train.journey_progress),
        "sched_vs_actual_diff": sched_vs_actual,
        "congestion_ratio":     round(occ / max(cap, 1), 3),
        "speed_limit_kmh":      section_info["speed_limit_kmh"],
    }


def build_congestion_features(
    section_id: str,
    occupancy_map: dict[str, list[str]],
    all_trains: list[TrainState],
) -> dict[str, float]:
    """
    Build a feature dict for the congestion classification model.
    Column order MUST match CONG_FEATURES in train_xgboost.py.
    """
    section_info = _get_section_info(section_id)
    tod          = _time_of_day_minutes()
    occ          = _count_occupancy(section_id, occupancy_map)
    cap          = section_info["section_capacity"]

    # Trains approaching = trains whose next section matches this section
    approaching = sum(
        1 for t in all_trains
        if t.current_section != section_id
        and t.next_station is not None
        # Simple heuristic: train is nearby (low journey progress delta)
    )
    # Better heuristic: count trains at immediately preceding node
    # (full impl requires network traversal — kept simple for Phase 2)

    avg_delay = (
        sum(t.delay_minutes for t in all_trains) / len(all_trains)
        if all_trains else 0.0
    )

    return {
        "section_length_km":     section_info["section_length_km"],
        "section_capacity":      float(cap),
        "section_occupancy":     float(occ),
        "is_single_track":       float(section_info["is_single_track"]),
        "trains_approaching":    float(approaching),
        "time_of_day_min":       float(tod),
        "is_peak_hour":          float(_is_peak(tod)),
        "avg_delay_in_section":  avg_delay,
        "congestion_ratio":      round(occ / max(cap, 1), 3),
        "future_load":           round((occ + approaching) / max(cap, 1), 3),
        "total_trains_network":  float(len(all_trains)),
        "speed_limit_kmh":       section_info["speed_limit_kmh"],
    }
