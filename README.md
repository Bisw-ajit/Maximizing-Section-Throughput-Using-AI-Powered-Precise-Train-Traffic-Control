# 🚂 RAILOPTIX — AI-Powered Precise Train Traffic Control System

> **Maximizing Railway Section Throughput & Resolving Network Bottlenecks via Hybrid Digital Twin, SimPy Discrete-Event Simulation Engine, and XGBoost AI Decision Pipeline**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![SimPy](https://img.shields.io/badge/Simulation-SimPy%204.1-3776AB.svg?style=flat-square)](https://simpy.readthedocs.io/)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost%202.0-FF6600.svg?style=flat-square)](https://xgboost.readthedocs.io/)
[![React 18](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB.svg?style=flat-square&logo=react)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-3178C6.svg?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![Tests](https://img.shields.io/badge/Tests-79%2F79%20Passing-brightgreen.svg?style=flat-square)]()
[![Status](https://img.shields.io/badge/Status-Capstone%20MVP-blue.svg?style=flat-square)]()

---

## 📑 Table of Contents
- [1. Product Overview](#1-product-overview)
- [2. Key Features](#2-key-features)
- [3. System UI Snapshots](#3-system-ui-snapshots)
- [4. Full System Architecture](#4-full-system-architecture)
  - [AI Decision Pipeline](#ai-decision-pipeline)
  - [ML Prediction Engine](#ml-prediction-engine)
  - [SimPy Simulation Engine](#simpy-discrete-event-engine)
  - [Digital Twin State](#digital-twin-state-synchronizer)
  - [NetworkX Graph Model](#networkx-railway-graph)
  - [KPI & Analytics](#kpi-calculation--metrics)
- [5. Quick Start](#5-quick-start--local-setup)
- [6. CLI Runner (make demo)](#6-cli-runner)
- [7. REST API Documentation](#7-rest-api-documentation)
- [8. Automated Testing](#8-automated-testing--verification)
- [9. Project Structure](#9-project-structure)
- [10. Author & License](#10-author--license)

---

## 1. Product Overview

**RAILOPTIX** is a 4th-year capstone engineering project implementing an AI-powered railway traffic control decision-support system for the **East Coast Railway (ECoR) Cuttack–Bhubaneswar–Khurda Road–Puri/Brahmapur corridor**.

The system combines four independent pillars to manage train conflicts, predict delays, and recommend interventions in real time:

| Pillar | Technology | Purpose |
|---|---|---|
| **Digital Twin** | In-memory state store + NetworkX | Live mirror of all train positions, sections, and occupancy |
| **DES Simulation** | SimPy 4.1 (threaded) | Discrete-event simulation of train movement with wall-clock pacing |
| **AI Decision Engine** | Multi-objective scoring + XAI | Conflict detection → candidate action synthesis → ranked recommendations |
| **ML Prediction** | XGBoost (trained, loaded) | Delay forecasting (MAE 2.9 min, R² 0.948) and congestion risk classification |

> 💡 **Core Design Principle**:
> *"Live data tells us what is happening now. Simulation tells us what could happen next. AI & optimization recommends what should be done."*

### 🗺️ Network Topology Covered

```text
                  CTK (Cuttack)
                       │
                 BGBR (Barang)
                       │
               BBS (Bhubaneswar)
                       │
                 RET (Retang)
                       │
            KUR (Khurda Road Junction)  ← Primary bottleneck node
             ┌─────────┴─────────┐
             │                   │
      (Puri Branch)     (Brahmapur Mainline)
       SIL (Sakhigopal)     BALU (Balugaon)
             │                   │
        PURI (Puri)       KLK (Khallikote)
                                 │
                          CAP (Chatrapur)
                                 │
                          BAM (Brahmapur)
```

**11 nodes · 10 track sections (single + double track) · 5 routes · 3 simulation scenarios**

---

## 2. Key Features

- **CTC Dispatch Board**: SVG-based schematic dispatch map with dark mode CTC aesthetics, real-time animated multi-train movement, section distance badges, and single-track occupancy highlights.
- **AI Conflict Resolution**: Automatic conflict detection across 4 conflict types (JUNCTION, CROSSING, SECTION, PLATFORM). Action candidates (HOLD, PRIORITIZE, CROSSING_WAIT, SPEED_ADVISORY) ranked via multi-objective scoring.
- **XAI Explanations**: Every AI recommendation includes a natural-language rationale explaining which scoring factors drove the decision.
- **XGBoost Delay Prediction**: Trained model predicts per-train delay (minutes) and per-section congestion risk from 14/12 real-time features. Heuristic fallback if model files absent.
- **Dual-Mode Analytics**: Headless baseline vs. AI-Assisted SimPy comparison with improvement metrics (delay reduction %, throughput gain).
- **KPI Persistence**: Simulation run KPIs stored in SQLite via SQLAlchemy; trend analysis and CSV/HTML-PDF report export.
- **Live Simulation Control**: Start, Pause, Resume, Reset, and speed multipliers (`1×`, `2×`, `5×`).
- **Siding Optimizer**: Station loop-line capacity analysis and deadlock prevention for junction saturation events.
- **Guided Demo**: 8-step interactive demo controller for presentations.

---

## 3. System UI Snapshots

### 🔴 1. Central Control Room — Live CTC Dispatch Board
*Real-time multi-train animated movement, section occupancies, and twin live event stream.*

![CTC Dispatch Board](docs/images/ctc_board_live.png)

---

### 2. Digital Twin — Active Train Telemetry
*Thread-safe state tracking and telemetry cards for all en-route trains.*

![Digital Twin View](docs/images/digital_twin_view.png)

---

### 3. Performance Analytics & KPI Optimization
*Baseline vs AI-Assisted comparison with delay reduction trends and section utilization.*

![KPI Analytics View](docs/images/kpi_analytics_view.png)

---

### 4. Scenario Management & Benchmarking
*Scenario loader with conflict injection, difficulty levels, and automatic KPI targets.*

![Scenario Management View](docs/images/scenario_management_view.png)

---

## 4. Full System Architecture

RAILOPTIX implements a 5-layer service architecture, **significantly expanded** beyond the initial Phase 1 design:

```text
╔══════════════════════════════════════════════════════════════════════╗
║              React / Vite Frontend  (port 5173)                      ║
║  DashboardView · LiveTwinView · ScenariosView · AnalyticsView        ║
╚══════════════════════════════════╤═══════════════════════════════════╝
                                   │  REST API (proxied via Vite)
                                   ▼
╔══════════════════════════════════════════════════════════════════════╗
║              FastAPI Backend  (port 8000)                            ║
║  9 routers: network · trains · twin · scenarios · simulation ·       ║
║             conflicts · recommendations · predictions · analytics    ║
╚══════╤══════════╤══════════╤══════════╤══════════╤══════════════════╝
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────────────┐
│ Digital  │ │ SimPy  │ │  AI    │ │  ML    │ │   Analytics Layer  │
│  Twin    │ │  DES   │ │Decision│ │ Predict│ │ KPI · Audit · CSV  │
│ (state)  │ │ Engine │ │ Engine │ │ Engine │ │ HTML/PDF Export    │
└────┬─────┘ └───┬────┘ └───┬────┘ └───┬────┘ └──────────┬─────────┘
     │           │          │          │                  │
     └───────────┴──────────┴──────────┘                  │
                        │                                 │
                        ▼                                 ▼
              ┌──────────────────┐              ┌──────────────────┐
              │  NetworkX Graph  │              │  SQLite Database │
              │  (11N · 10S · 5R)│              │  (SimulationRun) │
              └──────────────────┘              └──────────────────┘
```

### AI Decision Pipeline

```text
API Request → ConflictDetector.detect_all()
                ├── _detect_timetable_conflicts()   [from scenario JSON]
                └── _detect_live_occupancy_conflicts() [from DigitalTwin]
                         │
                         ▼
             ActionGenerator.generate_actions_for_conflict()
               → HOLD_TRAIN · PRIORITIZE_TRAIN · CROSSING_WAIT · SPEED_ADVISORY
                         │
                         ▼
             MultiObjectiveEvaluator.evaluate_candidates()
               weights: priority · delay_reduction · wait_reduction · throughput · congestion
                         │
                         ▼
             XAIExplainer.explain()
               → natural language rationale for top-ranked action
                         │
                         ▼
             DecisionEngine.apply_action()
               → mutates DigitalTwin state (train held / reprioritized)
```

### ML Prediction Engine

| Model | Type | Target | Features | Performance |
|---|---|---|---|---|
| `delay_model.json` | XGBRegressor | `next_delay_min` | 14 features | MAE 2.911 min · R² 0.9479 |
| `congestion_model.json` | XGBClassifier | `congestion_risk` | 12 features | ROC-AUC 0.9987 |

**Training**: See `colab/train_xgboost.py`. Data generated by `colab/generate_training_data.py` (50,000 synthetic ECoR corridor events).  
**Fallback**: If model files absent, `_heuristic_delay()` and `_heuristic_congestion()` activate automatically.

### SimPy Discrete-Event Engine

Each train runs as an autonomous SimPy generator process (`train_agent.py`):

1. Waits for scheduled departure time in simulation minutes
2. Requests a `SimPy.Resource` (capacity = section capacity) — **blocks** if single-line is occupied
3. Travels section: $\text{Travel Minutes} = \left(\frac{\text{Section km}}{\text{Speed km/h}}\right) \times 60$
4. Emits real-time events: `SECTION_ENTER`, `SECTION_EXIT`, `ARRIVAL`, `HELD`, `COMPLETED`
5. Updates Digital Twin via `emit_event()` (smooth `journey_progress` 0.0→1.0 for UI animation)

Simulation pacing: `REAL_SECONDS_PER_SIM_MIN_AT_1X × (1 / speed_multiplier)`, capped at 2s per tick.

### Digital Twin State Synchronizer

`digital_twin.py` — thread-safe in-memory state store with `threading.Lock()`:
- `_trains`: dict of `TrainState` dataclasses per `train_id`
- `_section_occupancy`: live occupancy count per section
- `_timetable`: scheduled arrival/departure per train
- `_scenario_data`: currently loaded scenario metadata
- `update_from_live()`: merges live RailRadar records (or ECoR mock fleet) into state

### NetworkX Railway Graph

`network_graph.py` — `nx.DiGraph` loaded from `scenarios/network/railoptix_network.json`:
- **Nodes (11)**: CTK, BGBR, BBS, RET, KUR, SIL, PURI, BALU, KLK, CAP, BAM
- **Raw Sections (10)**: directional track segments with `length_km`, `capacity`, `track_type`
- **Directed edges (20)**: bidirectional — each raw section creates `A→B` and `B→A` edges
- **Routes (5)**: `route_A` through `route_E` — ordered node sequences

### KPI Calculation & Metrics

| Metric | Formula | Target |
|---|---|---|
| **Throughput** | Trains completing their full route | Maximize |
| **Average Delay** | $\frac{\sum (\text{Actual Arrival} - \text{Scheduled Arrival})}{\text{Total Trains}}$ | Minimize |
| **Waiting Time** | Total cumulative minutes held at single-line sections | Minimize |
| **Section Utilization** | $\frac{\text{Completed Trains}}{\text{Total Trains}}$ | Maximize |

KPIs persisted to `railoptix.db` (SQLite) via `kpi_aggregator.py` for trend analysis.

---

## 5. Quick Start & Local Setup

### Prerequisites
- **Python**: `3.10+` (3.12 recommended)
- **Node.js**: `18.0+`
- **Git**, `pip`, `npm`

### Using Makefile (recommended)
```bash
# Clone and enter project
git clone <repo-url> && cd railoptix

# Install backend dependencies (creates .venv automatically)
make install

# Install frontend dependencies
make install-frontend

# Terminal 1: start backend
make backend

# Terminal 2: start frontend
make frontend
```

- **Dashboard**: `http://localhost:5173`
- **API Docs (Swagger)**: `http://127.0.0.1:8000/docs`

### Manual Setup

**Backend:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables (optional)
Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `RAILRADAR_API_KEY` | `""` | RailRadar live API key (leave empty to use ECoR mock fleet) |
| `RAILRADAR_MOCK_FALLBACK` | `true` | Use mock train data (always `true` without API key) |
| `CORS_ORIGINS` | localhost origins | Comma-separated allowed origins for production deployment |
| `MAPTILER_API_KEY` | `""` | MapTiler key for geographic map tile layer |

---

## 6. CLI Runner

Run a headless discrete-event simulation that prints the full event stream, timetable, and KPIs to stdout — no frontend required:

```bash
make demo
# or
source .venv/bin/activate && python run_railoptix.py
```

Sample output:
```text
🚆 SCENARIO EXECUTION: KHURDA ROAD JUNCTION MULTI-TRAIN CONFLICT [scenario_001]
📋 SCHEDULED DISPATCH & ROUTE TIMETABLE:
Train ID  | Train Name                   | Priority | Dept | Speed     | Route
T001      | Rajdhani Express 22812       | P1       | 6:00 | 110 km/h  | CTK → BBS → KUR → PURI
...
[06:00:00] 🟢 SECTION_ENTER | Train T001 ➜ Section CTK-BGBR    (SOUTHBOUND)
[06:19:27] 🚉 ARRIVAL       | Train T001 ➜ Arrived at BGBR (Delay: ON TIME) | Next: BBS
...
📊 EXECUTIVE PERFORMANCE KPI SUMMARY:
   • Throughput Rate:       5 / 5 trains completed (100.0%)
   • Average Train Delay:   4.2 minutes
```

---

## 7. REST API Documentation

Full interactive docs: `http://127.0.0.1:8000/docs`

### Network & Topology
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/network` | Full network topology: nodes, sections, routes |
| `GET` | `/api/network/sidings` | Station siding capacity and headroom |

### Digital Twin & Live Data
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/twin/state` | Full Digital Twin state snapshot |
| `POST` | `/api/twin/sync` | Push live/mock train records into twin |
| `GET` | `/api/trains/live` | All active trains with position and delay |
| `GET` | `/api/trains/live/provider-status` | RailRadar adapter status (live vs. mock) |
| `GET` | `/api/trains/{train_id}` | Single train detail |

### Scenarios
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/scenarios` | List all available scenarios |
| `POST` | `/api/scenarios/load` | Load scenario into twin and simulation engine |

### Simulation Engine
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/simulation/start` | Start DES simulation |
| `POST` | `/api/simulation/pause` | Pause simulation |
| `POST` | `/api/simulation/resume` | Resume paused simulation |
| `POST` | `/api/simulation/reset` | Reset to idle state |
| `POST` | `/api/simulation/speed` | Set speed multiplier `{"multiplier": 5.0}` |
| `GET` | `/api/simulation/status` | Simulation tick, status, completed trains |
| `GET` | `/api/simulation/kpis` | Live KPIs: throughput, delay, wait time, utilization |
| `GET` | `/api/simulation/events` | Event log (SECTION_ENTER, ARRIVAL, HELD, COMPLETED) |
| `POST` | `/api/simulation/stress-test` | Run corridor saturation stress test |

### AI Conflict Resolution
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/conflicts` | All active conflicts with type and severity |
| `GET` | `/api/conflicts/{id}` | Single conflict detail |
| `GET` | `/api/conflicts/{id}/candidates` | Action candidates for conflict |
| `POST` | `/api/recommendations` | Evaluate all conflicts and return ranked recommendations |
| `POST` | `/api/recommendations/apply` | Apply a selected action to the Digital Twin |

### ML Predictions
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/predictions` | Predict delay and congestion for all trains/sections |
| `GET` | `/api/predictions/train/{train_id}` | Single train delay forecast |
| `GET` | `/api/predictions/section/{section_id}` | Single section congestion risk |
| `GET` | `/api/predictions/status` | Predictor status (model loaded, metrics) |

### Analytics & Reporting
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/analytics/runs` | Historical simulation run KPIs from SQLite |
| `GET` | `/api/analytics/compare` | Baseline vs AI-Assisted comparison (dual-mode runner) |
| `GET` | `/api/analytics/audit-log` | Audit log entries with category filter |
| `GET` | `/api/analytics/export/csv` | Download KPI report as CSV |
| `GET` | `/api/analytics/export/report` | Download printable HTML/PDF performance report |

---

## 8. Automated Testing & Verification

RAILOPTIX has **79 tests across 12 test modules**, all passing:

```bash
# Run full test suite
make test

# or manually
source .venv/bin/activate
python -m unittest discover -s tests -v
```

```text
----------------------------------------------------------------------
Ran 79 tests in 1.6s

OK
```

| Test Module | Tests | Coverage |
|---|---|---|
| `test_phase1_core.py` | 3 | Network graph, scenario loader, digital twin |
| `test_api_and_simulation.py` | 7 | Health, network, simulation lifecycle, API contract |
| `test_rail7_live_adapter.py` | 9 | RailRadar adapter, network mapper, ECoR fleet |
| `test_rail9_action_generator.py` | 6 | Conflict detection, action synthesis, recommendations |
| `test_rail10_decision_selector.py` | 6 | Decision engine evaluate and apply pipeline |
| `test_rail13_dual_simulation.py` | 6 | Baseline vs AI-Assisted comparison |
| `test_rail14_kpi_aggregator.py` | 6 | KPI SQLite persistence |
| `test_rail15_xai_explainer.py` | 7 | XAI natural language explanation |
| `test_rail16_siding_stress.py` | 5 | Siding optimizer capacity analysis |
| `test_rail17_analytics_compare.py` | 3 | Analytics compare endpoint |
| `test_rail18_demo_and_export.py` | 6 | Audit logger, CSV/HTML export |
| `test_delay_predictor.py` | 15 | XGBoost predictor + feature engineering |

---

## 9. Project Structure

```text
railoptix/
├── Makefile                          # Developer task runner
├── run_railoptix.py                  # CLI headless simulation runner
├── .env.example                      # Environment variable template
├── README.md
│
├── backend/
│   ├── main.py                       # FastAPI app entry point, lifespan, CORS, routers
│   ├── requirements.txt              # Python dependencies
│   ├── core/
│   │   ├── config.py                 # Pydantic Settings (env vars)
│   │   └── database.py               # SQLAlchemy async engine
│   ├── api/                          # 9 FastAPI routers
│   │   ├── network.py, trains.py, twin.py, scenarios.py
│   │   ├── simulation.py, conflicts.py, recommendations.py
│   │   ├── predictions.py, analytics.py
│   ├── models/models.py              # SQLAlchemy ORM (9 tables; SimulationRun actively used)
│   ├── schemas/schemas.py            # Pydantic response schemas
│   ├── simulation/
│   │   ├── engine.py                 # SimulationEngine: DES lifecycle, threading, pacing
│   │   ├── train_agent.py            # Per-train SimPy generator process
│   │   ├── dual_runner.py            # Headless baseline vs AI comparison runner
│   │   └── stress_runner.py          # Corridor saturation stress test
│   ├── services/
│   │   ├── twin/
│   │   │   ├── network_graph.py      # RailNetwork: NetworkX DiGraph (11N, 10S, 5R)
│   │   │   ├── digital_twin.py       # DigitalTwin: thread-safe state store
│   │   │   ├── scenario_loader.py    # ScenarioLoader: JSON load + timetable compute
│   │   │   └── network_mapper.py     # Station alias resolution, GPS→node, progress
│   │   ├── conflict/
│   │   │   └── conflict_detector.py  # ConflictDetector: timetable + live occupancy
│   │   ├── decision/
│   │   │   ├── action_generator.py   # CandidateAction synthesis (4 action types)
│   │   │   ├── evaluator.py          # Multi-objective scoring (5 weights)
│   │   │   ├── engine.py             # DecisionEngine orchestrator
│   │   │   └── explainer.py          # XAI rule-based NL explanation
│   │   ├── prediction/
│   │   │   ├── delay_predictor.py    # XGBoost predictor + heuristic fallback
│   │   │   └── feature_engineering.py # 14+12 feature vectors from TrainState
│   │   ├── analytics/
│   │   │   ├── kpi_aggregator.py     # SQLite KPI persistence, trend analysis
│   │   │   ├── audit_logger.py       # Thread-safe in-memory audit log
│   │   │   └── report_exporter.py    # CSV + HTML/PDF report generation
│   │   └── optimization/
│   │       └── siding_optimizer.py   # Station loop capacity analysis
│   ├── ml_models/
│   │   ├── delay_model.json          # XGBRegressor (MAE 2.9min, R² 0.948)
│   │   ├── congestion_model.json     # XGBClassifier (ROC-AUC 0.999)
│   │   ├── feature_columns.json      # Feature metadata and model metrics
│   │   └── README.md                 # Model retrain instructions
│   └── providers/
│       ├── base_adapter.py           # Abstract adapter interface
│       └── railradar/adapter.py      # RailRadar API + ECoR mock fleet
│
├── frontend/
│   ├── src/
│   │   ├── views/                    # DashboardView, LiveTwinView, ScenariosView, AnalyticsView
│   │   ├── components/
│   │   │   ├── dashboard/            # NetworkMap, KpiBar, SimulationControls, RecommendationPanel
│   │   │   ├── demo/                 # DemoController (8-step guided demo)
│   │   │   ├── layout/               # Header
│   │   │   └── trains/               # TrainDetailDrawer
│   │   ├── hooks/useRailData.ts      # React Query polling hooks
│   │   ├── stores/useAppStore.ts     # Zustand global state
│   │   ├── services/apiClient.ts     # Typed API client
│   │   └── types/api.ts              # TypeScript types for all API contracts
│   ├── vite.config.ts                # Port 5173, proxy /api → :8000
│   └── package.json
│
├── scenarios/
│   ├── network/railoptix_network.json          # 11 nodes, 10 sections, 5 routes
│   ├── scenario_001_khurda_conflict.json       # 5 trains, KUR junction conflict (primary demo)
│   ├── scenario_002_baseline.json              # No-conflict baseline
│   └── scenario_003_stress_saturation.json     # Corridor saturation stress test
│
├── tests/                            # 79 tests across 12 modules (all passing)
│
├── colab/
│   ├── generate_training_data.py     # Synthetic 50k-sample ECoR event data generator
│   ├── train_xgboost.py              # Full XGBoost training script (regressor + classifier)
│   └── requirements.txt              # Colab environment dependencies
│
└── docs/
    ├── images/                       # UI screenshots (4 views)
    ├── KNOWN_LIMITATIONS.md          # Engineering disclosure: known issues and technical debt
    ├── PROJECT_ROADMAP_AND_JIRA_SPRINTS.md  # 3-phase sprint plan (RAIL-1 to RAIL-18)
    └── REVIEW_1_PROGRESS_REPORT.md
```

---

## 10. Author & License

- **Author**: Biswajit ([@Bisw-ajit](https://github.com/Bisw-ajit))
- **Project Type**: 4th-Year Major Engineering Project — East Coast Railway, Cuttack Division (7th Semester)
- **Domain**: AI · Discrete-Event Simulation · Digital Twin · Railway Operations Research
- **License**: MIT License — free for academic and research use.

---

> **Known Limitations**: See [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) for an honest engineering disclosure of the project's current technical debt and deployment prerequisites.
