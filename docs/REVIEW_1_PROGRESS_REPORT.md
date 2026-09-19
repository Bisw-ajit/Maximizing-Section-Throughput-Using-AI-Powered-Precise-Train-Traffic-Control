# 🚂 RAILOPTIX — AI-Powered Precise Train Traffic Control System
## Capstone Project 7th Semester — 1st Review Comprehensive Progress Report

**Institution:** Department of Computer Science & Engineering  
**Project Title:** RAILOPTIX: AI-Powered Precise Train Traffic Control Decision Support System  
**Review Stage:** 1st Review (Phase 1 Deliverables)  
**Team Composition:** 3 Members (2 User Stories Completed per Member = 6 User Stories Total)  
**JIRA Tracking Project:** `RAIL` (Cloud Instance: [sophisticate.atlassian.net](https://sophisticate.atlassian.net))  
**Date of Submission:** August 29, 2026  

---

## 📑 Executive Summary

RAILOPTIX is a software-based railway traffic decision-support system built around a hybrid Digital Twin and a SimPy discrete-event simulation engine. For the 1st Project Review, the team has achieved 100% completion of the foundational architectural milestones (Phase 1):
1. **Corridor Topological Infrastructure & Scenario Ingestion** (`NetworkX` Graph Model)
2. **In-Memory Digital Twin State Synchronizer** (Authoritative Single Source of Truth)
3. **SimPy Discrete-Event Simulation Engine** (Virtual Time Movement Loop & Playback Controls)
4. **Spatial-Temporal Conflict Detection Engine** (Single-Track Bottleneck Hazard Warning)
5. **Central Control Room (CTC) Schematic Dispatch Board** (React 18 + SVG Dynamic Visualizer)
6. **Real-Time Telemetry KPI Analytics & Train Inspection Drawer** (Live Metrics & Zustand Store)

---

## 👥 Team Work Allocation & JIRA Traceability Matrix

| Student / Role | User Story ID | JIRA Key | User Story Summary | Status | Story Points |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Student 1** (Backend Lead) | `US-01` | [RAIL-1](https://sophisticate.atlassian.net/browse/RAIL-1) | Implement Railway Network Topology Graph & Scenario Ingestion Engine | **DONE** | 5 SP |
| **Student 1** (Backend Lead) | `US-02` | [RAIL-2](https://sophisticate.atlassian.net/browse/RAIL-2) | Construct In-Memory Digital Twin State Manager & Telemetry Synchronizer | **DONE** | 5 SP |
| **Student 2** (Simulation Lead) | `US-03` | [RAIL-3](https://sophisticate.atlassian.net/browse/RAIL-3) | Implement SimPy Discrete-Event Simulation Core & Virtual Time Controls | **DONE** | 8 SP |
| **Student 2** (Simulation Lead) | `US-04` | [RAIL-4](https://sophisticate.atlassian.net/browse/RAIL-4) | Develop Single-Track Bottleneck Conflict Detection & Warning Engine | **DONE** | 8 SP |
| **Student 3** (Frontend Lead) | `US-05` | [RAIL-5](https://sophisticate.atlassian.net/browse/RAIL-5) | Build Central Control Room (CTC) Schematic Dispatch Board & Live Animation | **DONE** | 5 SP |
| **Student 3** (Frontend Lead) | `US-06` | [RAIL-6](https://sophisticate.atlassian.net/browse/RAIL-6) | Implement Real-Time Telemetry KPI Bar & Train Detail Drawer | **DONE** | 5 SP |

---

# 📋 Individual User Story Reports

```
========================================================================================
                          STUDENT 1: BACKEND & DIGITAL TWIN LEAD
========================================================================================
```

### 🔹 User Story 1: `RAIL-1` (Topological Railway Network Graph & Scenario Loader)
* **User Story ID:** `US-01` / `RAIL-1`
* **Objective:**
  > *"As a Railway Operations Planner, I want a digital topological graph representation of the high-density railway corridor (Cuttack–Bhubaneswar–Khurda Road–Puri/Brahmapur) along with automated timetable and scenario loaders, so that the system can accurately model junctions, single/double track sections, block capacities, and route travel schedules."*
* **Work Completed:**
  - Designed the directed multigraph infrastructure model using Python `NetworkX`.
  - Configured 11 nodes (`CTK`, `BGBR`, `BBS`, `RET`, `KUR`, `SIL`, `PURI`, `BALU`, `KLK`, `CAP`, `BAM`) and 10 track sections with length, operational speed limits, and track multiplicity.
  - Implemented dynamic timetable calculation in `scenario_loader.py`, calculating intermediate section traversal runtimes and schedule milestones.
* **Current Status:** `DONE / VERIFIED`
* **Verifiable Evidence:**
  - **Source Code:** `backend/services/twin/network_graph.py`, `backend/services/twin/scenario_loader.py`
  - **Data Asset:** `scenarios/network/railoptix_network.json`, `scenarios/scenario_001_khurda_conflict.json`
  - **API Verification:** `GET /api/v1/network/graph`, `GET /api/v1/scenarios`
  - **Unit Test:** `test_network_graph_loaded`, `test_scenario_loader_and_timetable` in `tests/test_phase1_core.py`

---

### 🔹 User Story 2: `RAIL-2` (Digital Twin State Synchronizer & Telemetry Store)
* **User Story ID:** `US-02` / `RAIL-2`
* **Objective:**
  > *"As a Train Traffic Controller, I want an in-memory Digital Twin state synchronizer that maintains live train positions, speeds, delay states, and section occupancies, so that the control system has an authoritative single source of truth for the entire railway corridor."*
* **Work Completed:**
  - Developed thread-safe in-memory state synchronizer managing real-time telemetry attributes.
  - Added atomic state update routines (`update_train_state`) tracking current block section, position offset (km), speed (km/h), delay (mins), and statuses (`ON_TIME`, `DELAYED`, `HELD`, `RUNNING`).
  - Integrated dynamic section occupancy registry and event publishing pipeline.
* **Current Status:** `DONE / VERIFIED`
* **Verifiable Evidence:**
  - **Source Code:** `backend/services/twin/digital_twin.py`, `backend/api/twin.py`, `backend/schemas/train.py`
  - **API Verification:** `GET /api/v1/twin/state`, `POST /api/v1/twin/reset`
  - **Unit Test:** `test_digital_twin_state` in `tests/test_phase1_core.py`

---

```
========================================================================================
                     STUDENT 2: SIMULATION & CONFLICT DETECTION LEAD
========================================================================================
```

### 🔹 User Story 3: `RAIL-3` (SimPy Discrete-Event Simulation Core & Virtual Time Controls)
* **User Story ID:** `US-03` / `RAIL-3`
* **Objective:**
  > *"As an Operations Researcher, I want a SimPy discrete-event simulation engine capable of stepping through train movements with playback speed controls (1x, 2x, 5x, pause, resume), so that we can forecast future train interactions and test dispatching strategies in virtual time."*
* **Work Completed:**
  - Implemented the discrete-event simulation core using `SimPy 4.1`.
  - Modeled asynchronous processes for train dispatching, block section travel times, signal stops, and platform dwell times.
  - Created REST lifecycle controllers for Start, Pause, Resume, Reset, and speed multiplier modulation.
  - Connected simulation step callbacks to Digital Twin state synchronizer for real-time telemetry streaming.
* **Current Status:** `DONE / VERIFIED`
* **Verifiable Evidence:**
  - **Source Code:** `backend/simulation/simpy_engine.py`, `backend/api/simulation.py`, `backend/schemas/simulation.py`
  - **API Verification:** `POST /api/v1/simulation/start`, `POST /api/v1/simulation/pause`, `POST /api/v1/simulation/speed`
  - **Integration Verification:** 180 simulated minutes multi-train continuous execution.

---

### 🔹 User Story 4: `RAIL-4` (Single-Track Bottleneck Conflict Detection Engine)
* **User Story ID:** `US-04` / `RAIL-4`
* **Objective:**
  > *"As a Chief Train Controller, I want an automated conflict-detection module that continuously evaluates single-track occupancy and headway constraints, so that crossing and following conflicts at bottlenecks (e.g., Khurda Road–Puri single line) are flagged before causing deadlocks."*
* **Work Completed:**
  - Developed spatial-temporal conflict detection logic for single-line railway sections.
  - Implemented crossing collision hazard alarms for opposing train movements on shared sections (e.g., Section `KUR-SIL-PURI`).
  - Added headway violation buffer algorithms for same-direction trains along high-density trunk routes.
  - Formatted alert payloads with severity levels (`CRITICAL`, `WARNING`, `ADVISORY`), involved trains, bottleneck location, and estimated time-to-conflict.
* **Current Status:** `DONE / VERIFIED`
* **Verifiable Evidence:**
  - **Source Code:** `backend/services/conflicts/conflict_detector.py`, `backend/api/conflicts.py`
  - **Scenario Validation:** `scenarios/scenario_001_khurda_conflict.json`
  - **API Verification:** `GET /api/v1/conflicts/active`, `GET /api/v1/predictions/conflicts`

---

```
========================================================================================
                   STUDENT 3: FRONTEND DISPATCHER UI & ANALYTICS LEAD
========================================================================================
```

### 🔹 User Story 5: `RAIL-5` (Central Control Room CTC Schematic Dispatch Board)
* **User Story ID:** `US-05` / `RAIL-5`
* **Objective:**
  > *"As a Dispatcher in the Central Control Room, I want a dark-themed SVG-based Centralized Traffic Control (CTC) Schematic Dispatch Board, so that I can visualize real-time train positions, track occupancy glows, and station nodes across the entire network."*
* **Work Completed:**
  - Engineered the vector-based CTC schematic board in React 18, Vite, and TypeScript.
  - Configured coordinate projection displaying 11 stations with double-track and single-track branch rendering.
  - Created animated train markers with speed callouts, direction arrows, and category color codes (Premium: Amber, Express: Cyan, Freight: Violet).
  - Implemented dynamic track occupancy highlights and pulsing red hazard halos on conflicted track blocks.
* **Current Status:** `DONE / VERIFIED`
* **Verifiable Evidence:**
  - **Source Code:** `frontend/src/components/dashboard/NetworkMap.tsx`, `frontend/src/components/dashboard/NetworkMap.css`, `frontend/src/views/LiveTwinView.tsx`
  - **UI Route:** `http://localhost:5173/` and `http://localhost:5173/twin`

---

### 🔹 User Story 6: `RAIL-6` (Real-Time Telemetry KPI Bar & Train Inspection Drawer)
* **User Story ID:** `US-06` / `RAIL-6`
* **Objective:**
  > *"As a Railway Operations Supervisor, I want a real-time KPI bar and train telemetry drawer, so that I can monitor network throughput, average delay, waiting time, and individual train schedule adherence in real-time."*
* **Work Completed:**
  - Built the live telemetry KPI bar tracking Throughput (trains/hr), Average Delay (minutes), Total Waiting Time, and Section Utilization (%).
  - Developed the Train Detail Drawer displaying train metadata, itinerary milestones, scheduled vs actual arrival, speed, and delay status.
  - Set up global state management via Zustand and reactive polling hooks (`useRailData.ts`).
  - Integrated simulation control interface with playback buttons and speed selectors.
* **Current Status:** `DONE / VERIFIED`
* **Verifiable Evidence:**
  - **Source Code:** `frontend/src/components/dashboard/KpiBar.tsx`, `frontend/src/components/trains/TrainDetailDrawer.tsx`, `frontend/src/stores/useAppStore.ts`, `frontend/src/hooks/useRailData.ts`, `frontend/src/components/dashboard/SimulationControls.tsx`
  - **UI Route:** Telemetry and KPI panels at `http://localhost:5173`

---

## 🎯 Verification & Defense Checklist for Review 1

| Verification Category | Method of Demonstration | Expected Result |
| :--- | :--- | :--- |
| **JIRA Live Audit** | Open Jira Project `RAIL` on [sophisticate.atlassian.net](https://sophisticate.atlassian.net) | All 6 stories (`RAIL-1` to `RAIL-6`) marked `DONE` with detailed technical acceptance criteria. |
| **API Endpoints** | Navigate to `http://localhost:8000/docs` (FastAPI Swagger) | Test `/network/graph`, `/twin/state`, `/conflicts/active`, `/simulation/start`. |
| **UI Demonstration** | Open `http://localhost:5173` | Start simulation, observe real-time train movement, track glows, KPI telemetry bar, and click train to view drawer. |
| **Conflict Trigger** | Select `scenario_001_khurda_conflict` | Observe hazard warning alert on the Khurda Road–Puri single line bottleneck. |
