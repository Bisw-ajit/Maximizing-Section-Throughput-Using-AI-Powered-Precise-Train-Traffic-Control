# RAILOPTIX — Known Limitations & Technical Debt

**Last updated:** 2026-09-19  
**Scope:** Academic capstone project (4th-year CS) — honest engineering disclosure  

---

## Architectural Limitations

### 1. Hardcoded Train IDs in Dual-Mode Comparison (HIGH)
**File:** `backend/simulation/dual_runner.py` lines 195–215  
**Description:** The `compare()` method in `DualModeSimulator` applies AI interventions with hardcoded train IDs (`T001`, `T003`, `T004`) and fixed train names (`"Rajdhani Express"`, `"Puri Express"`). These are specific to `scenario_001`.  
**Impact:** Running the AI comparison with `scenario_002` or `scenario_003` applies interventions to the correct scenario's trains by ID, but the summary narrative text and intervention descriptions are scenario_001-specific.  
**Workaround:** The system still functions correctly for scenario_001 (the primary demo scenario). Other scenarios' comparison percentages are computed correctly; only the applied-interventions description list is hardcoded.  
**Planned fix:** Derive AI interventions dynamically from `conflict_detector` + `action_generator` pipeline.

---

### 2. Circular Dependency via Local Imports (MEDIUM)
**File:** `backend/simulation/engine.py` — `emit_event()` method  
**Description:** `SimulationEngine.emit_event()` imports `digital_twin` locally inside the method body to avoid a circular import. The root cause is tight coupling: the simulation engine directly mutates DigitalTwin state.  
**Impact:** Minor — the system works correctly. Local imports are slightly slower on first call.  
**Proper fix:** Implement an event bus (publisher/subscriber pattern) — the engine emits typed events, the digital twin subscribes and updates itself. This decouples simulation from state management.  
**Current status:** Documented workaround is acceptable for capstone scope.

---

### 3. REST Polling (No WebSockets/SSE) (MEDIUM)
**Description:** The React frontend polls backend REST endpoints every N seconds (via TanStack React Query). There is no WebSocket or Server-Sent Events (SSE) connection for real-time push.  
**Impact:** A 1–3 second polling delay exists between simulator state changes and frontend updates. For live CTC dispatch (real production), this would be a UX problem.  
**Workaround:** Fast polling interval (1–2s) provides adequate responsiveness for demo/capstone purposes.  
**Planned fix:** Implement SSE stream at `/api/simulation/stream` for real-time event push.

---

### 4. Mock-Only Live Train Data (LOW — by design)
**File:** `backend/providers/railradar/adapter.py`  
**Description:** `RAILRADAR_MOCK_FALLBACK=True` is the default. The actual RailRadar API is never called in normal operation because no API key is provided.  
**Impact:** The "Live Train" view always shows the 6-train ECoR mock fleet, not real-time Indian Railways data.  
**Note:** The mock fleet is realistic — actual ECoR train numbers (20836, 22823, 12831, 12822, 18417), realistic delays, and correct corridor positions.  
**To enable real data:** Obtain a RailRadar API key, add `RAILRADAR_API_KEY=your_key` to `.env`.

---

### 5. Pydantic Schemas Not Used in API Responses (LOW)
**File:** `backend/schemas/schemas.py`  
**Description:** `APIResponse[T]`, `TrainStatus`, `ConflictType`, and other Pydantic schemas are defined but not used by any API endpoint. All endpoints return raw Python `dict` objects.  
**Impact:** OpenAPI docs (`/docs`) show less precise response schemas. Two parallel enum definitions exist (`schemas.py` vs individual service files).  
**Planned fix:** Refactor API endpoints to use `APIResponse[T]` as the declared response model.

---

### 6. `trains_approaching` Approximation in Feature Engineering (LOW)
**File:** `backend/services/prediction/feature_engineering.py` line 74  
**Description:** The `trains_approaching` feature (used by the congestion model) approximates the count of trains approaching a section by counting all trains whose `next_station` is not `None`. This does not actually check graph proximity.  
**Impact:** Minor — the congestion model still performs (ROC-AUC 0.9987 on synthetic data). The approximation may slightly over-count approaching trains.  
**Planned fix:** Use NetworkX graph traversal to identify trains within N hops of the target section.

---

## Deployment Limitations (not ready for production without these)

| Limitation | Description |
|---|---|
| **No Authentication** | API endpoints are completely open. No JWT, no API keys, no session management. |
| **CORS (fixed)** | Was: wildcard `"*"`. Now: localhost-only defaults. Production needs explicit origin list in `.env`. |
| **No Docker** | No `Dockerfile` or `docker-compose.yml`. Manual setup required. |
| **No CI/CD** | No GitHub Actions, no automated test-on-PR, no deployment pipeline. |
| **SQLite database** | `railoptix.db` is a file-based SQLite DB. Not suitable for concurrent multi-user access. Use PostgreSQL for production. |
| **Single-process** | FastAPI + SimPy run in one process. Simulation thread blocking is managed via `threading.Thread` but there is no worker process isolation. |
| **No rate limiting** | All API endpoints are unthrottled. |
| **No model versioning** | XGBoost models stored as plain files. No MLflow, no model registry, no A/B testing. |

---

## Testing Gaps

| Gap | Description |
|---|---|
| No integration test for dual_runner hardcoded IDs | The hardcoded scenario_001 train ID issue is not caught by any test |
| No performance benchmarks | No test verifies simulation throughput or API response time SLAs |
| No concurrent access tests | DigitalTwin has a Lock() but there are no multi-threaded stress tests for it |
| No adversarial input tests | No tests for malformed scenario JSON, invalid train IDs in API calls, etc. |

---

*This document is maintained as part of the production handover package. Update when limitations are resolved.*
