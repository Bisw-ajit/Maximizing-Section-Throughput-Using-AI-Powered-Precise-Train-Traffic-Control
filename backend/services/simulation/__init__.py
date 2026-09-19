"""
RAILOPTIX — services/simulation namespace package
==================================================
NOTE: This package is intentionally empty.

The actual SimPy discrete-event simulation engine lives in:
  backend/simulation/          ← SimulationEngine, train_agent, dual_runner, stress_runner

This `services/simulation/` directory was created during early architectural planning
as a placeholder for simulation-related services. The simulation code was ultimately
placed directly under `backend/simulation/` to avoid overly deep nesting.

Do not add simulation services here — use backend/simulation/ instead.
"""
