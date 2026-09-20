export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: {
    code: string;
    message: string;
  } | null;
}

export interface Node {
  node_id: string;
  name: string;
  node_type: string;
  latitude: number;
  longitude: number;
  platform_count?: number;
  is_junction?: boolean;
}

export interface Section {
  section_id: string;
  from_node: string;
  to_node: string;
  length_km: number;
  capacity: number;
  allowed_movements: string;
  is_bidirectional: boolean;
}

export interface Route {
  route_id: string;
  name: string;
  direction: string;
  node_sequence: string[];
}

export interface NetworkData {
  nodes: Node[];
  sections: Section[];
  routes: Route[];
}

export interface Train {
  train_id: string;
  train_number: string;
  name: string;
  priority: number;
  current_node: string | null;
  current_section: string | null;
  direction: string | null;
  status: 'SCHEDULED' | 'EN_ROUTE' | 'AT_STATION' | 'DELAYED' | 'HELD' | 'COMPLETED';
  delay_minutes: number;
  next_station: string | null;
  route_id: string;
  last_updated: string;
  data_source: 'LIVE' | 'RECENTLY_UPDATED' | 'STALE' | 'SIMULATION';
  is_live: boolean;
  staleness_seconds: number;
  journey_progress: number;
}

export interface DigitalTwinState {
  scenario_id: string | null;
  last_sync: string | null;
  trains: Train[];
  section_occupancy: Record<string, string[]>;
  train_count: number;
}

export interface Scenario {
  scenario_id: string;
  name: string;
  description: string;
  network_id: string;
  train_count: number;
  difficulty: string;
  file?: string;
}

export interface SimulationStatus {
  status: 'IDLE' | 'RUNNING' | 'PAUSED' | 'COMPLETED';
  current_tick: number;
  elapsed_sim_minutes: number;
  scenario_id: string | null;
  trains_in_flight: number;
  completed_trains: number;
  total_trains: number;
  speed_multiplier: number;
}

export interface SimulationKPIs {
  throughput: number;
  average_delay: number;
  waiting_time: number;
  utilization: number;
}

export interface SimulationEvent {
  type: string;
  train_id: string;
  tick: number;
  timestamp: string;
  [key: string]: any;
}

// ─── AI Conflict & Recommendation Types (RAIL-9 / RAIL-10 / RAIL-11) ──────────

export interface ConflictItem {
  conflict_id: string;
  conflict_type: 'JUNCTION_CONFLICT' | 'CROSSING_CONFLICT' | 'SECTION_CONFLICT' | 'PLATFORM_CONFLICT';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  location: string;
  train_ids: string[];
  predicted_time_minutes: number;
  time_to_conflict_minutes: number;
  description: string;
  status: string;
  detected_at: string;
}

export interface CandidateActionItem {
  recommendation_id: string;
  conflict_id: string;
  action_type: 'HOLD_TRAIN' | 'PRIORITIZE_TRAIN' | 'CROSSING_WAIT' | 'SPEED_ADVISORY' | 'REROUTE';
  target_train_id: string;
  target_train_name: string;
  target_train_priority: number;
  target_location: string;
  parameters: Record<string, any>;
  score: number;
  sub_scores: {
    priority: number;
    delay: number;
    wait_time: number;
    throughput: number;
    congestion: number;
  };
  reason: string;
  description?: string;
  trade_off_explanation: string;
  expected_delay_change: number;
  expected_waiting_change: number;
  feasible: boolean;
  feasibility_reason: string;
  evaluated_at: string;
}

export interface RecommendationResponse {
  candidates: CandidateActionItem[];
  recommended: CandidateActionItem | null;
  total_candidates: number;
  feasible_count: number;
  conflicts_count: number;
  active_weights?: Record<string, number>;
  message?: string;
}

export interface AppliedActionItem {
  action_id: string;
  action_type: string;
  target_train_id: string;
  target_train_name: string;
  location: string;
  applied_at: string;
  status: string;
  new_status?: string;
  added_delay_minutes?: number;
  siding_station?: string;
}

// ─── Predictive ML Heatmap Types (RAIL-12) ──────────────────────────────────

export interface SectionCongestionItem {
  section_id: string;
  congestion_risk: number;
  risk_probability: number;
  severity: 'CLEAR' | 'ADVISORY' | 'WARNING' | 'CRITICAL';
  model_used: string;
}

export interface TrainDelayPredictionItem {
  train_id: string;
  train_number: string;
  current_delay_min: number;
  predicted_delay_min: number;
  delay_delta_min: number;
  trend: 'WORSENING' | 'IMPROVING' | 'STABLE';
  model_used: string;
}

export interface PredictionsData {
  train_predictions: TrainDelayPredictionItem[];
  section_congestion: Record<string, SectionCongestionItem>;
  summary: {
    avg_predicted_delay_min: number;
    at_risk_sections: string[];
    at_risk_count: number;
    trains_predicted: number;
    model_loaded: boolean;
  };
  horizon_minutes: number;
  generated_at: string;
}

// ─── Explainable AI (XAI) Types (RAIL-15) ───────────────────────────────────

export interface FactorAttributionItem {
  factor_name: string;
  impact_pct: number;
  direction: string;
  description: string;
}

export interface CounterfactualItem {
  alternative_action: string;
  alternative_type: string;
  projected_consequence: string;
  why_rejected: string;
}

export interface RegulatoryComplianceItem {
  rule_code: string;
  rule_name: string;
  compliance_status: string;
  authority: string;
  explanation: string;
}

export interface DecisionExplanationData {
  recommendation_id: string;
  conflict_id: string;
  action_type: string;
  target_train_name: string;
  target_train_id: string;
  target_location: string;
  composite_utility_score: number;
  executive_summary: string;
  key_drivers: FactorAttributionItem[];
  counterfactuals: CounterfactualItem[];
  regulatory_compliance: RegulatoryComplianceItem[];
  confidence_score: number;
  model_attribution: Record<string, string>;
  generated_at: string;
}

// ── RAIL-16: Siding Capacity & Stress Testing ───────────────────────────────

export interface StationSidingInfo {
  station_id: string;
  station_name: string;
  total_capacity: number;
  occupied_count: number;
  available_headroom: number;
  utilization_pct: number;
  is_congested: boolean;
  is_saturated: boolean;
  occupying_trains: string[];
}

export interface SidingStatusData {
  sidings: Record<string, StationSidingInfo>;
  total_stations_monitored: number;
  congested_stations: string[];
  saturated_stations: string[];
}

export interface StressTestRequest {
  scenario_id?: string;
  additional_delay_minutes?: number;
  enforce_siding_limits?: boolean;
}

export interface StressTestResultData {
  test_id: string;
  scenario_id: string;
  total_trains: number;
  duration_minutes: number;
  recovery_time_ms: number;
  deadlocks_prevented: number;
  resilience_score: number;
  baseline_delay: number;
  ai_optimized_delay: number;
  delay_saved_pct: number;
  p1_delay_eliminated: boolean;
  station_siding_peaks: Record<string, number>;
  details: Record<string, any>;
  tested_at: string;
}

// ── RAIL-17: Performance Analytics & Benchmarks ─────────────────────────────

export interface TrainRunMetric {
  train_id: string;
  train_number: string;
  name: string;
  priority: number;
  scheduled_arrival_min: number;
  actual_arrival_min: number;
  delay_minutes: number;
  wait_time_minutes: number;
  status?: string;
}

export interface SimulationStrategyResult {
  strategy: string;
  scenario_id: string;
  throughput: number;
  total_trains: number;
  average_delay: number;
  p1_delay: number;
  waiting_time: number;
  conflict_count: number;
  utilization: number;
  run_id?: string;
  train_results: TrainRunMetric[];
  events_count: number;
  duration_sim_minutes: number;
}

export interface AnalyticsComparisonData {
  scenario_id: string;
  compared_at: string;
  baseline: SimulationStrategyResult;
  ai_assisted: SimulationStrategyResult;
  metrics_comparison: {
    delay_improvement_pct: number;
    p1_delay_improvement_pct: number;
    waiting_time_reduction_pct: number;
    conflict_reduction_pct: number;
    throughput_improvement_pct: number;
    summary: string;
  };
  applied_ai_interventions: string[];
}

export interface AnalyticsSummaryData {
  scenario_id: string | null;
  total_runs_evaluated: number;
  baseline_runs_count: number;
  ai_runs_count: number;
  average_baseline_delay: number;
  average_ai_delay: number;
  cumulative_delay_saved_minutes: number;
  average_delay_reduction_pct: number;
  p1_schedule_protection_rate: number;
  conflict_resolution_rate: number;
  average_throughput: number;
  latest_run_id: string | null;
  computed_at: string;
}

export interface AnalyticsRunRecord {
  run_id: string;
  scenario_id: string;
  strategy: string;
  start_time: string;
  end_time: string;
  throughput: number;
  average_delay: number;
  p1_delay?: number;
  waiting_time: number;
  conflict_count: number;
  utilization: number;
  train_results?: TrainRunMetric[];
}

export interface AuditLogEntry {
  entry_id: string;
  timestamp: string;
  category: string;
  event_type: string;
  train_id: string | null;
  location: string;
  message: string;
  details: Record<string, any>;
}



