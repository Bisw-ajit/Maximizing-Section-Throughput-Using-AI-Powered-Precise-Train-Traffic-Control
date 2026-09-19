#!/usr/bin/env python3
"""
RAILOPTIX — Command-Line Simulation & Digital Twin Output Runner
Executes the SimPy Discrete-Event Simulation engine and outputs full
chronological telemetry, conflict resolution logs, and KPI analytics.
"""

import sys
import time
from datetime import datetime, timezone
import simpy

from backend.services.twin.network_graph import rail_network
from backend.services.twin.scenario_loader import scenario_loader
from backend.services.twin.digital_twin import digital_twin
from backend.simulation.engine import simulation_engine, SimulationStrategy
from backend.simulation.train_agent import train_process


def format_sim_time(sim_minutes: float) -> str:
    hh = int(sim_minutes // 60)
    mm = int(sim_minutes % 60)
    ss = int((sim_minutes * 60) % 60)
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def run_scenario(scenario_id: str):
    print("=" * 90)
    scen = scenario_loader.load(scenario_id, rail_network)
    tt = scenario_loader.compute_timetable(scen, rail_network)
    digital_twin.load_scenario(scen, tt)
    simulation_engine.load_scenario(scen, rail_network, tt, strategy=SimulationStrategy.BASELINE)

    print(f"🚆 SCENARIO EXECUTION: {scen['name'].upper()} [{scen['scenario_id']}]")
    print(f"📖 Context: {scen.get('description', 'N/A')}")
    print(f"🎯 Difficulty Level: {scen.get('difficulty', 'MEDIUM')}")
    print(f"🚂 Fleet Size: {len(scen['trains'])} active trains")
    print("-" * 90)

    # 1. Scheduled Timetable
    print("📋 SCHEDULED DISPATCH & ROUTE TIMETABLE:")
    print(f"{'Train ID':<9} | {'Train Name':<28} | {'Priority':<8} | {'Dept':<6} | {'Speed':<9} | {'Route'}")
    print("-" * 90)
    for t in scen["trains"]:
        route_info = rail_network.get_route(t["route_id"])
        route_name = route_info["name"] if route_info else t["route_id"]
        print(f"{t['train_id']:<9} | {t['name']:<28} | P{t['priority']:<7} | {t['scheduled_departure']:<6} | {str(t['avg_speed_kmh']) + ' km/h':<9} | {route_name}")
    print("-" * 90)

    # 2. Network Topology Sections
    print(f"🗺️  ACTIVE CORRIDOR SECTIONS ({len(rail_network.get_all_sections())} sections):")
    for s in rail_network.get_all_sections():
        track_tag = f"[{s.get('track_type', 'SINGLE')} TRACK, Cap: {s.get('capacity', 1)}]"
        print(f"   • {s['section_id']:<10} ({s['from_node']} ➜ {s['to_node']}) — {s['length_km']} km {track_tag}")
    print("-" * 90)

    # 3. SimPy Simulation Process Execution
    print("⚡ SIMULATING DISCRETE-EVENT RAILWAY TRAFFIC RUN...")
    simulation_engine.env = simpy.Environment()

    # Configure shared physical section resources
    raw_secs = getattr(rail_network, "raw_sections", list(rail_network.sections.values()))
    simulation_engine.section_resources.clear()
    for section in raw_secs:
        capacity = section.get("capacity", 1)
        res = simpy.Resource(simulation_engine.env, capacity=capacity)
        fwd_id = section["section_id"]
        simulation_engine.section_resources[fwd_id] = res
        rev_id = f"{section['to_node']}-{section['from_node']}"
        simulation_engine.section_resources[rev_id] = res

    for train in scen["trains"]:
        route_sections = rail_network.get_route_sections(train["route_id"])
        train_tt = tt.get(train["train_id"], {})
        simulation_engine.env.process(
            train_process(
                env=simulation_engine.env,
                train=train,
                route_sections=route_sections,
                section_resources=simulation_engine.section_resources,
                timetable=train_tt,
                engine=simulation_engine,
            )
        )

    # Step the SimPy discrete event engine to completion
    simulation_engine.env.run()

    print(f"✅ SIMULATION COMPLETED — Total Events Dispatched: {len(simulation_engine.events)}")
    print("-" * 90)

    # 4. Chronological Telemetry Log
    print("📡 DIGITAL TWIN EVENT STREAM & TRAIN MOVEMENTS:")
    for ev in simulation_engine.events:
        t_str = format_sim_time(ev["tick"])
        ev_type = ev["type"]
        tid = ev["train_id"]

        if ev_type == "SECTION_ENTER":
            print(f"  [{t_str}] 🟢 SECTION_ENTER | Train {tid:<4} ➜ Section {ev['section_id']:<10} ({ev.get('direction', 'SOUTHBOUND')})")
        elif ev_type == "SECTION_EXIT":
            print(f"  [{t_str}] ⚪ SECTION_EXIT  | Train {tid:<4} ➜ Cleared Section {ev['section_id']}")
        elif ev_type == "ARRIVAL":
            next_st = f"| Next: {ev['next_station']}" if ev.get('next_station') else "| Final Terminal"
            delay_str = f"+{ev['delay_minutes']:.2f}m" if ev['delay_minutes'] > 0 else "ON TIME"
            print(f"  [{t_str}] 🚉 ARRIVAL       | Train {tid:<4} ➜ Arrived at {ev['node_id']:<4} (Delay: {delay_str:<7}) {next_st}")
        elif ev_type == "HELD":
            print(f"  [{t_str}] 🔴 HELD (CONFLICT)| Train {tid:<4} ➜ Held at {ev['section_id']:<10} for {ev['wait_minutes']:.2f} min (Single-line contention)")
        elif ev_type == "COMPLETED":
            print(f"  [{t_str}] 🏁 COMPLETED     | Train {tid:<4} ➜ Route Completed (Final Delay: +{ev['final_delay_minutes']:.2f} min)")

    print("-" * 90)

    # 5. Performance KPIs
    kpis = simulation_engine.get_kpis()
    print("📊 EXECUTIVE PERFORMANCE KPI SUMMARY:")
    print(f"   • Throughput Rate:       {kpis.get('throughput')} / {len(scen['trains'])} trains completed (100.0%)")
    print(f"   • Average Train Delay:   {kpis.get('average_delay')} minutes")
    print(f"   • Cumulative Wait Time:  {kpis.get('waiting_time')} minutes")
    print(f"   • Section Utilization:   {kpis.get('utilization') * 100:.1f}%")
    print("=" * 90)
    print()


def main():
    print("""
==========================================================================================
 🚂  RAILOPTIX — AI-POWERED PRECISE TRAIN TRAFFIC CONTROL & DIGITAL TWIN SYSTEM
     East Coast Railway Corridor (Cuttack – Bhubaneswar – Khurda Road – Puri / Brahmapur)
==========================================================================================
    """)
    rail_network.load_from_json("scenarios/network/railoptix_network.json")
    print(f"Loaded Network Topology: {len(rail_network.get_all_nodes())} Nodes | {len(rail_network.get_all_sections())} Sections | {len(rail_network.get_all_routes())} Routes\n")

    # Run available scenarios
    for s in ["scenario_001", "scenario_002"]:
        run_scenario(s)


if __name__ == "__main__":
    main()
