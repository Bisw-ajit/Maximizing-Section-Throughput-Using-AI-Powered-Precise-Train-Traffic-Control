"""
RAILOPTIX — Synthetic Training Data Generator
=============================================
Run this script FIRST (locally or on Colab) to generate training data.
It simulates thousands of train movement events across the RAILOPTIX network
and saves them as CSV files for XGBoost training.

Output files:
  - data/delay_regression_data.csv          -> train delay prediction model
  - data/congestion_classification_data.csv -> train congestion risk model

Usage:
  python generate_training_data.py
  python generate_training_data.py --samples 50000
"""

import random
import csv
import os
import argparse

# ─────────────────────────────────────────────────────────────────────────────
# RAILOPTIX Network Definition (mirrors railoptix_network.json)
# ─────────────────────────────────────────────────────────────────────────────

SECTIONS = {
    "CTK-BGBR": {"length_km": 15.0, "capacity": 2, "speed_limit_kmh": 100, "is_single_track": False},
    "BGBR-BBS": {"length_km": 12.0, "capacity": 2, "speed_limit_kmh": 100, "is_single_track": False},
    "BBS-RET":  {"length_km": 8.0,  "capacity": 2, "speed_limit_kmh": 80,  "is_single_track": False},
    "RET-KUR":  {"length_km": 10.0, "capacity": 2, "speed_limit_kmh": 90,  "is_single_track": False},
    "KUR-SIL":  {"length_km": 18.0, "capacity": 1, "speed_limit_kmh": 80,  "is_single_track": True},  # BOTTLENECK
    "SIL-PURI": {"length_km": 11.0, "capacity": 1, "speed_limit_kmh": 70,  "is_single_track": True},  # BOTTLENECK
    "KUR-BALU": {"length_km": 20.0, "capacity": 1, "speed_limit_kmh": 75,  "is_single_track": True},
    "BALU-KLK": {"length_km": 25.0, "capacity": 1, "speed_limit_kmh": 80,  "is_single_track": True},
    "KLK-CAP":  {"length_km": 30.0, "capacity": 1, "speed_limit_kmh": 85,  "is_single_track": True},
    "CAP-BAM":  {"length_km": 22.0, "capacity": 1, "speed_limit_kmh": 85,  "is_single_track": True},
}

TRAIN_PRIORITIES = [1, 2, 3, 4, 5]
PRIORITY_NAMES   = {1: "PREMIUM", 2: "SUPERFAST", 3: "EXPRESS", 4: "PASSENGER", 5: "FREIGHT"}
DELAY_BASE       = {"PREMIUM": 2, "SUPERFAST": 5, "EXPRESS": 8, "PASSENGER": 12, "FREIGHT": 20}
DELAY_STD        = {"PREMIUM": 3, "SUPERFAST": 7, "EXPRESS": 10, "PASSENGER": 15, "FREIGHT": 25}

PEAK_HOURS = set(list(range(6*60, 10*60)) + list(range(17*60, 21*60)))


def is_peak(t):
    return t in PEAK_HOURS


def compute_speed(speed_limit, current_delay, occupancy, capacity):
    load_factor = min(occupancy / max(capacity, 1), 1.0)
    speed = speed_limit * (1.0 - 0.2 * load_factor)
    if current_delay > 10:
        speed = min(speed * 1.1, speed_limit)
    return max(speed * random.uniform(0.85, 1.05), 20.0)


def compute_next_delay(section_id, current_delay, priority, occupancy, capacity, peak, trains_ahead, speed_kmh, progress):
    sec = SECTIONS[section_id]
    nd = current_delay
    congestion = max(0, occupancy - capacity + 1)
    nd += congestion * random.uniform(3.0, 8.0)
    if sec["is_single_track"]:
        if occupancy >= capacity:
            nd += random.uniform(5.0, 20.0)
        elif trains_ahead > 0:
            nd += random.uniform(2.0, 8.0)
    if peak:
        nd += random.uniform(2.0, 6.0)
    nd = max(0, nd - (6 - priority) * random.uniform(0.5, 2.0))
    if progress > 0.7:
        nd += random.uniform(0, 3.0)
    nd += random.gauss(0, 1.5)
    return round(max(0.0, nd), 2)


def compute_congestion_risk(section_id, occupancy, capacity, trains_approaching, peak):
    sec = SECTIONS[section_id]
    future = occupancy + trains_approaching
    if future >= capacity:
        return 1
    if sec["is_single_track"] and peak and trains_approaching >= 1:
        return 1 if random.random() < 0.65 else 0
    if peak and future >= capacity - 1:
        return 1 if random.random() < 0.4 else 0
    return 0


def gen_delay_sample():
    sid  = random.choice(list(SECTIONS.keys()))
    sec  = SECTIONS[sid]
    pri  = random.choice(TRAIN_PRIORITIES)
    cap  = sec["capacity"]
    occ  = random.randint(0, min(cap + 1, 3))
    tod  = random.randint(0, 24*60-1)
    pk   = is_peak(tod)
    cd   = max(0.0, random.gauss(DELAY_BASE[PRIORITY_NAMES[pri]], DELAY_STD[PRIORITY_NAMES[pri]]))
    ta   = random.randint(0, 3)
    prog = random.uniform(0.0, 1.0)
    spd  = compute_speed(sec["speed_limit_kmh"], cd, occ, cap)
    sva  = cd * random.uniform(0.8, 1.2)
    nd   = compute_next_delay(sid, cd, pri, occ, cap, pk, ta, spd, prog)
    return {
        "current_delay_min":    round(cd, 2),
        "section_length_km":    sec["length_km"],
        "section_capacity":     cap,
        "section_occupancy":    occ,
        "is_single_track":      int(sec["is_single_track"]),
        "train_priority":       pri,
        "speed_kmh":            round(spd, 2),
        "time_of_day_min":      tod,
        "is_peak_hour":         int(pk),
        "trains_ahead":         ta,
        "journey_progress":     round(prog, 3),
        "sched_vs_actual_diff": round(sva, 2),
        "congestion_ratio":     round(occ / max(cap, 1), 3),
        "speed_limit_kmh":      sec["speed_limit_kmh"],
        "next_delay_min":       nd,
    }


def gen_congestion_sample():
    sid  = random.choice(list(SECTIONS.keys()))
    sec  = SECTIONS[sid]
    cap  = sec["capacity"]
    occ  = random.randint(0, min(cap + 1, 3))
    ta   = random.randint(0, 3)
    tod  = random.randint(0, 24*60-1)
    pk   = is_peak(tod)
    avg_d = random.uniform(0, 25)
    total = random.randint(2, 12)
    risk  = compute_congestion_risk(sid, occ, cap, ta, pk)
    return {
        "section_length_km":     sec["length_km"],
        "section_capacity":      cap,
        "section_occupancy":     occ,
        "is_single_track":       int(sec["is_single_track"]),
        "trains_approaching":    ta,
        "time_of_day_min":       tod,
        "is_peak_hour":          int(pk),
        "avg_delay_in_section":  round(avg_d, 2),
        "congestion_ratio":      round(occ / max(cap, 1), 3),
        "future_load":           round((occ + ta) / max(cap, 1), 3),
        "total_trains_network":  total,
        "speed_limit_kmh":       sec["speed_limit_kmh"],
        "congestion_risk":       risk,
    }


def main(n=30_000):
    os.makedirs("data", exist_ok=True)

    # Delay regression
    delay_rows = [gen_delay_sample() for _ in range(n)]
    with open("data/delay_regression_data.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(delay_rows[0].keys()))
        w.writeheader(); w.writerows(delay_rows)
    print(f"✅  delay_regression_data.csv  ({n} rows)")

    # Congestion classification
    cong_rows = [gen_congestion_sample() for _ in range(n)]
    with open("data/congestion_classification_data.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cong_rows[0].keys()))
        w.writeheader(); w.writerows(cong_rows)
    print(f"✅  congestion_classification_data.csv  ({n} rows)")

    delays    = [r["next_delay_min"] for r in delay_rows]
    congested = sum(r["congestion_risk"] for r in cong_rows)
    print(f"\n📊 Stats  |  Avg delay: {sum(delays)/len(delays):.2f} min  |  Congested: {congested/n*100:.1f}%")
    print("🎯 Next: Upload data/ folder + train_xgboost.py to Colab and run!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=30_000)
    args = parser.parse_args()
    random.seed(42)
    main(args.samples)
