from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional, Any
from datetime import datetime
from enum import Enum

T = TypeVar("T")


# ─── Enums ────────────────────────────────────────────────────────────────────

class DataSource(str, Enum):
    LIVE = "LIVE"
    RECENTLY_UPDATED = "RECENTLY_UPDATED"
    STALE = "STALE"
    SIMULATION = "SIMULATION"


class TrainStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    EN_ROUTE = "EN_ROUTE"
    AT_STATION = "AT_STATION"
    DELAYED = "DELAYED"
    HELD = "HELD"
    COMPLETED = "COMPLETED"


class ConflictType(str, Enum):
    SECTION_CONFLICT = "SECTION_CONFLICT"
    JUNCTION_CONFLICT = "JUNCTION_CONFLICT"
    CROSSING_CONFLICT = "CROSSING_CONFLICT"
    PLATFORM_CONFLICT = "PLATFORM_CONFLICT"


class ConflictSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ConflictStatus(str, Enum):
    PREDICTED = "PREDICTED"
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"


class SimulationStrategy(str, Enum):
    BASELINE = "BASELINE"
    AI_ASSISTED = "AI_ASSISTED"


class SimulationAction(str, Enum):
    START = "START"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    RESET = "RESET"


# ─── Generic API Response ──────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str


class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None

    @classmethod
    def ok(cls, data: T) -> "APIResponse[T]":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, code: str, message: str) -> "APIResponse[None]":
        return cls(success=False, data=None, error=ErrorDetail(code=code, message=message))


# ─── Network Schemas ───────────────────────────────────────────────────────────

class NodeSchema(BaseModel):
    node_id: str
    name: str
    node_type: str
    latitude: float
    longitude: float


class SectionSchema(BaseModel):
    section_id: str
    from_node: str
    to_node: str
    length_km: float
    capacity: int
    allowed_movements: str
    is_bidirectional: bool


class RouteSchema(BaseModel):
    route_id: str
    name: str
    node_sequence: List[str]
    direction: str


class NetworkSchema(BaseModel):
    nodes: List[NodeSchema]
    sections: List[SectionSchema]
    routes: List[RouteSchema]


# ─── Train Schemas ─────────────────────────────────────────────────────────────

class TrainSchema(BaseModel):
    train_id: str
    train_number: str
    name: str
    priority: int
    current_node: Optional[str] = None
    current_section: Optional[str] = None
    direction: Optional[str] = None
    status: str
    delay_minutes: float
    next_station: Optional[str] = None
    route_id: Optional[str] = None
    last_updated: datetime
    data_source: str
    is_live: bool
    staleness_seconds: float = 0.0
    journey_progress: float = 0.0


class TrainListSchema(BaseModel):
    trains: List[TrainSchema]
    total: int
    last_updated: datetime
    source: str
    is_live: bool


# ─── Conflict Schemas ──────────────────────────────────────────────────────────

class ConflictSchema(BaseModel):
    conflict_id: str
    conflict_type: str
    severity: str
    location: str
    train_ids: List[str]
    predicted_time: datetime
    reason: str
    status: str


class ConflictListSchema(BaseModel):
    conflicts: List[ConflictSchema]
    total: int


# ─── Recommendation Schemas ────────────────────────────────────────────────────

class RecommendationSchema(BaseModel):
    recommendation_id: str
    conflict_id: str
    action_type: str
    affected_trains: List[str]
    score: float
    reason: str
    expected_delay_change: float
    expected_waiting_change: float
    feasible: bool


class RecommendationResponseSchema(BaseModel):
    candidates: List[RecommendationSchema]
    recommended: Optional[RecommendationSchema] = None
    total_candidates: int
    feasible_count: int


# ─── Scenario Schemas ──────────────────────────────────────────────────────────

class ScenarioSchema(BaseModel):
    scenario_id: str
    name: str
    description: str
    network_id: str
    created_at: datetime
    is_active: bool
    train_count: int = 0


class ScenarioListSchema(BaseModel):
    scenarios: List[ScenarioSchema]


class LoadScenarioRequest(BaseModel):
    scenario_id: str


# ─── Simulation Schemas ────────────────────────────────────────────────────────

class SimulationRunSchema(BaseModel):
    run_id: str
    scenario_id: str
    strategy: str
    start_time: datetime
    end_time: Optional[datetime] = None
    throughput: int
    average_delay: float
    waiting_time: float
    conflict_count: int
    utilization: float


class SimulationStatusSchema(BaseModel):
    status: str
    current_tick: float
    elapsed_sim_minutes: float
    scenario_id: Optional[str] = None
    trains_in_flight: int
    speed_multiplier: float


# ─── Prediction Schemas ────────────────────────────────────────────────────────

class PredictionInput(BaseModel):
    scenario_id: str
    horizon_minutes: int = Field(default=30, ge=5, le=120)


class TrainPrediction(BaseModel):
    train_id: str
    train_number: str
    predicted_arrival: Optional[datetime] = None
    predicted_delay_minutes: float
    congestion_risk: float = Field(ge=0.0, le=1.0)
    next_station: Optional[str] = None


class PredictionResponse(BaseModel):
    predictions: List[TrainPrediction]
    section_congestion: dict
    horizon_minutes: int
    generated_at: datetime


# ─── What-If Schemas ───────────────────────────────────────────────────────────

class WhatIfInput(BaseModel):
    scenario_id: str
    action_type: str
    affected_train_ids: List[str]
    horizon_minutes: int = Field(default=60, ge=10, le=180)


class WhatIfResponse(BaseModel):
    action_type: str
    delay_change_minutes: float
    waiting_change_minutes: float
    throughput_change: int
    conflict_change: int
    utilization_change: float
    feasible: bool
    summary: str


# ─── Analytics Schemas ─────────────────────────────────────────────────────────

class KpiComparisonSchema(BaseModel):
    baseline: Optional[SimulationRunSchema] = None
    ai_assisted: Optional[SimulationRunSchema] = None
    delay_improvement_pct: Optional[float] = None
    conflict_reduction_pct: Optional[float] = None
    throughput_improvement_pct: Optional[float] = None
    runs: List[SimulationRunSchema] = []
