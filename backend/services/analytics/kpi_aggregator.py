"""
RAILOPTIX — Historical Simulation Database Service & KPI Aggregator
====================================================================
Persists simulation runs, tracks lifetime benchmarks, and computes macro KPIs:
  - Cumulative corridor delay minutes saved by AI
  - Priority 1 (Rajdhani/Vande Bharat) schedule protection rate
  - Bottleneck conflict resolution rate
  - Multi-run trend analytics for reporting and dashboard visualization

Fulfills: JIRA RAIL-14.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from threading import Lock

from sqlalchemy import select, desc
from ...core.database import AsyncSessionLocal
from ...models.models import SimulationRun


class KPIAggregatorService:
    """
    Manages historical simulation run records and computes lifetime aggregate analytics.
    Thread-safe with combined in-memory caching and persistent database backup.
    """

    def __init__(self):
        self._lock = Lock()
        self._runs_cache: List[Dict[str, Any]] = []

    async def save_run(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a simulation run into the database and update analytics cache."""
        run_id = run_data.get("run_id") or f"RUN_{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        start_time = run_data.get("start_time")
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time)
            except Exception:
                start_time = now
        elif not start_time:
            start_time = now

        end_time = run_data.get("end_time")
        if isinstance(end_time, str):
            try:
                end_time = datetime.fromisoformat(end_time)
            except Exception:
                end_time = now
        elif not end_time:
            end_time = now

        record = {
            "run_id": run_id,
            "scenario_id": run_data.get("scenario_id", "scenario_001"),
            "strategy": run_data.get("strategy", "BASELINE"),
            "start_time": start_time.isoformat() if isinstance(start_time, datetime) else str(start_time),
            "end_time": end_time.isoformat() if isinstance(end_time, datetime) else str(end_time),
            "throughput": int(run_data.get("throughput", 0)),
            "average_delay": float(run_data.get("average_delay", 0.0)),
            "p1_delay": float(run_data.get("p1_delay", 0.0)),
            "waiting_time": float(run_data.get("waiting_time", 0.0)),
            "conflict_count": int(run_data.get("conflict_count", 0)),
            "utilization": float(run_data.get("utilization", 0.0)),
            "train_results": run_data.get("train_results", []),
        }

        # Save to database
        try:
            async with AsyncSessionLocal() as session:
                db_run = SimulationRun(
                    run_id=run_id,
                    scenario_id=record["scenario_id"],
                    strategy=record["strategy"],
                    start_time=start_time if isinstance(start_time, datetime) else now,
                    end_time=end_time if isinstance(end_time, datetime) else now,
                    throughput=record["throughput"],
                    average_delay=record["average_delay"],
                    waiting_time=record["waiting_time"],
                    conflict_count=record["conflict_count"],
                    utilization=record["utilization"],
                )
                session.add(db_run)
                await session.commit()
        except Exception:
            # Fallback gracefully to cache if DB table creation is pending
            pass

        with self._lock:
            # Check duplicate
            existing_idx = next((i for i, r in enumerate(self._runs_cache) if r["run_id"] == run_id), None)
            if existing_idx is not None:
                self._runs_cache[existing_idx] = record
            else:
                self._runs_cache.append(record)

        return record

    async def get_runs(
        self,
        limit: int = 50,
        scenario_id: Optional[str] = None,
        strategy: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent simulation runs matching optional filters."""
        # Query database first
        db_records: List[Dict[str, Any]] = []
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(SimulationRun).order_by(desc(SimulationRun.start_time)).limit(limit)
                if scenario_id:
                    stmt = stmt.where(SimulationRun.scenario_id == scenario_id)
                if strategy:
                    stmt = stmt.where(SimulationRun.strategy == strategy.upper())

                res = await session.execute(stmt)
                runs = res.scalars().all()
                for r in runs:
                    db_records.append({
                        "run_id": r.run_id,
                        "scenario_id": r.scenario_id,
                        "strategy": r.strategy,
                        "start_time": r.start_time.isoformat() if r.start_time else None,
                        "end_time": r.end_time.isoformat() if r.end_time else None,
                        "throughput": r.throughput,
                        "average_delay": round(r.average_delay, 2),
                        "waiting_time": round(r.waiting_time, 2),
                        "conflict_count": r.conflict_count,
                        "utilization": round(r.utilization, 3),
                    })
        except Exception:
            pass

        # If DB returned records, sync with cache
        if db_records:
            return db_records

        # Fallback to in-memory cache
        with self._lock:
            filtered = list(self._runs_cache)
            if scenario_id:
                filtered = [r for r in filtered if r["scenario_id"] == scenario_id]
            if strategy:
                filtered = [r for r in filtered if r["strategy"].upper() == strategy.upper()]
            return sorted(filtered, key=lambda r: r["start_time"], reverse=True)[:limit]

    def get_summary(self, scenario_id: Optional[str] = None) -> Dict[str, Any]:
        """Compute comprehensive macro KPI benchmarks across all historical simulation runs."""
        with self._lock:
            runs = list(self._runs_cache)

        if scenario_id:
            runs = [r for r in runs if r["scenario_id"] == scenario_id]

        baseline_runs = [r for r in runs if r["strategy"] == "BASELINE"]
        ai_runs = [r for r in runs if r["strategy"] == "AI_ASSISTED"]

        total_runs = len(runs)
        if total_runs == 0:
            return {
                "total_runs": 0,
                "baseline_count": 0,
                "ai_count": 0,
                "baseline_avg_delay": 0.0,
                "ai_avg_delay": 0.0,
                "total_delay_minutes_saved": 0.0,
                "avg_delay_reduction_pct": 0.0,
                "p1_protection_rate_pct": 100.0,
                "conflict_resolution_rate_pct": 100.0,
                "recent_trends": [],
                "message": "No historical runs recorded yet.",
            }

        base_avg_delay = (
            sum(r["average_delay"] for r in baseline_runs) / len(baseline_runs)
            if baseline_runs else 0.0
        )
        ai_avg_delay = (
            sum(r["average_delay"] for r in ai_runs) / len(ai_runs)
            if ai_runs else 0.0
        )

        # Total minutes saved
        delay_saved_per_run = max(0.0, base_avg_delay - ai_avg_delay)
        total_delay_saved = round(delay_saved_per_run * len(ai_runs), 1)

        # Average delay reduction percentage
        delay_reduction_pct = 0.0
        if base_avg_delay > 0:
            delay_reduction_pct = round(((base_avg_delay - ai_avg_delay) / base_avg_delay) * 100, 1)

        # P1 priority protection rate (P1 delay <= 1.0 min)
        p1_protected_count = sum(1 for r in ai_runs if r.get("p1_delay", 0.0) <= 1.0)
        p1_protection_rate = (
            round((p1_protected_count / len(ai_runs)) * 100, 1)
            if ai_runs else 100.0
        )

        # Conflict resolution success rate
        total_baseline_conflicts = sum(r.get("conflict_count", 0) for r in baseline_runs)
        total_ai_conflicts = sum(r.get("conflict_count", 0) for r in ai_runs)
        conflict_res_rate = 100.0
        if total_baseline_conflicts > 0:
            resolved = max(0, total_baseline_conflicts - total_ai_conflicts)
            conflict_res_rate = round((resolved / total_baseline_conflicts) * 100, 1)

        # Build trend points for charting
        recent_trends = []
        for i, r in enumerate(runs[-10:]):
            recent_trends.append({
                "run_index": i + 1,
                "run_id": r.get("run_id", f"RUN_{i+1:03d}"),
                "strategy": r.get("strategy", "BASELINE"),
                "delay": r.get("average_delay", 0.0),
                "wait_time": r.get("waiting_time", 0.0),
                "timestamp": r.get("start_time", datetime.now(timezone.utc).isoformat()),
            })

        return {
            "total_runs": total_runs,
            "baseline_count": len(baseline_runs),
            "ai_count": len(ai_runs),
            "baseline_avg_delay": round(base_avg_delay, 2),
            "ai_avg_delay": round(ai_avg_delay, 2),
            "total_delay_minutes_saved": total_delay_saved,
            "avg_delay_reduction_pct": delay_reduction_pct,
            "p1_protection_rate_pct": p1_protection_rate,
            "conflict_resolution_rate_pct": conflict_res_rate,
            "recent_trends": recent_trends,
        }

    def clear_cache(self) -> None:
        with self._lock:
            self._runs_cache.clear()


# Singleton
kpi_aggregator = KPIAggregatorService()
