import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from '../services/apiClient';
import {
  NetworkData,
  DigitalTwinState,
  Scenario,
  SimulationStatus,
  SimulationKPIs,
  SimulationEvent,
  Train,
  ConflictItem,
  RecommendationResponse,
  PredictionsData,
  DecisionExplanationData,
  SidingStatusData,
  StressTestResultData,
  StressTestRequest,
  AnalyticsComparisonData,
  AnalyticsSummaryData,
  AnalyticsRunRecord,
  AuditLogEntry,
} from '../types/api';

export function useNetwork() {
  return useQuery<NetworkData>({
    queryKey: ['network'],
    queryFn: () => fetchApi<NetworkData>('/network'),
    staleTime: Infinity, // Network topology is static
  });
}

export function useDigitalTwin(enabled = true) {
  return useQuery<DigitalTwinState>({
    queryKey: ['digitalTwin'],
    queryFn: () => fetchApi<DigitalTwinState>('/twin/state'),
    refetchInterval: enabled ? 1000 : false, // Poll state every second when active
  });
}

export function useScenarios() {
  return useQuery<{ scenarios: Scenario[]; total: number }>({
    queryKey: ['scenarios'],
    queryFn: () => fetchApi<{ scenarios: Scenario[]; total: number }>('/scenarios'),
  });
}

export function useSimulationStatus(enabled = true) {
  return useQuery<SimulationStatus>({
    queryKey: ['simulationStatus'],
    queryFn: () => fetchApi<SimulationStatus>('/simulation/status'),
    refetchInterval: enabled ? 1000 : false,
  });
}

export function useSimulationKPIs() {
  return useQuery<SimulationKPIs>({
    queryKey: ['simulationKPIs'],
    queryFn: () => fetchApi<SimulationKPIs>('/simulation/kpis'),
    refetchInterval: 2000,
  });
}

export function useSimulationEvents(limit = 20) {
  return useQuery<{ events: SimulationEvent[]; total: number }>({
    queryKey: ['simulationEvents', limit],
    queryFn: () => fetchApi<{ events: SimulationEvent[]; total: number }>(`/simulation/events?limit=${limit}`),
    refetchInterval: 1000,
  });
}

export function useTrainDetail(trainId: string | null) {
  return useQuery<Train>({
    queryKey: ['train', trainId],
    queryFn: () => fetchApi<Train>(`/trains/${trainId}`),
    enabled: !!trainId,
  });
}

export function useScenarioActions() {
  const queryClient = useQueryClient();

  const loadScenario = useMutation({
    mutationFn: (scenarioId: string) =>
      fetchApi<{ scenario_id: string; message: string }>('/scenarios/load', {
        method: 'POST',
        body: JSON.stringify({ scenario_id: scenarioId }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['digitalTwin'] });
      queryClient.invalidateQueries({ queryKey: ['simulationStatus'] });
      queryClient.invalidateQueries({ queryKey: ['simulationKPIs'] });
    },
  });

  const resetScenario = useMutation({
    mutationFn: () => fetchApi<{ message: string }>('/scenarios/reset', { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['digitalTwin'] });
      queryClient.invalidateQueries({ queryKey: ['simulationStatus'] });
    },
  });

  return { loadScenario, resetScenario };
}

export function useSimulationControlActions() {
  const queryClient = useQueryClient();

  const startSimulation = useMutation({
    mutationFn: () => fetchApi('/simulation/start', { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['simulationStatus'] }),
  });

  const pauseSimulation = useMutation({
    mutationFn: () => fetchApi('/simulation/pause', { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['simulationStatus'] }),
  });

  const resumeSimulation = useMutation({
    mutationFn: () => fetchApi('/simulation/resume', { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['simulationStatus'] }),
  });

  const resetSimulation = useMutation({
    mutationFn: () => fetchApi('/simulation/reset', { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['simulationStatus'] }),
  });

  const setSpeed = useMutation({
    mutationFn: (multiplier: number) =>
      fetchApi('/simulation/speed', {
        method: 'POST',
        body: JSON.stringify({ multiplier }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['simulationStatus'] }),
  });

  return { startSimulation, pauseSimulation, resumeSimulation, resetSimulation, setSpeed };
}

// ─── AI Conflict & Recommendation Hooks (RAIL-11) ───────────────────────────

export function useConflicts() {
  return useQuery<{ conflicts: ConflictItem[]; total: number; critical_count: number; high_count: number }>({
    queryKey: ['conflicts'],
    queryFn: () => fetchApi('/conflicts'),
    refetchInterval: 2000,
  });
}

export function useRecommendations(profile = 'BALANCED') {
  return useQuery<RecommendationResponse>({
    queryKey: ['recommendations', profile],
    queryFn: () =>
      fetchApi<RecommendationResponse>('/recommendations', {
        method: 'POST',
        body: JSON.stringify({ profile }),
      }),
    refetchInterval: 3000,
  });
}

export function useRecommendationProfiles() {
  return useQuery<{ profiles: Record<string, any>; default_profile: string }>({
    queryKey: ['recommendationProfiles'],
    queryFn: () => fetchApi('/recommendations/profiles'),
    staleTime: Infinity,
  });
}

export function useApplyRecommendation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (actionId: string) =>
      fetchApi<{ success: boolean; message: string; applied_action: any }>('/recommendations/apply', {
        method: 'POST',
        body: JSON.stringify({ action_id: actionId }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['digitalTwin'] });
      queryClient.invalidateQueries({ queryKey: ['simulationStatus'] });
      queryClient.invalidateQueries({ queryKey: ['simulationKPIs'] });
      queryClient.invalidateQueries({ queryKey: ['predictions'] });
    },
  });
}

// ─── Predictive ML Heatmap Hook (RAIL-12) ───────────────────────────────────

export function usePredictions(horizonMinutes = 30, enabled = true) {
  return useQuery<PredictionsData>({
    queryKey: ['predictions', horizonMinutes],
    queryFn: () =>
      fetchApi<PredictionsData>('/predictions', {
        method: 'POST',
        body: JSON.stringify({ horizon_minutes: horizonMinutes, include_sections: true }),
      }),
    refetchInterval: enabled ? 3500 : false,
  });
}

// ─── Explainable AI (XAI) Hook (RAIL-15) ────────────────────────────────────

export function useDecisionExplanation(recommendationId: string | null) {
  return useQuery<DecisionExplanationData>({
    queryKey: ['decisionExplanation', recommendationId],
    queryFn: () => fetchApi<DecisionExplanationData>(`/recommendations/${recommendationId}/explain`),
    enabled: !!recommendationId,
    staleTime: 60000,
  });
}

// ─── Siding Capacity & Stress Testing Hooks (RAIL-16) ───────────────────────

export function useSidingStatus(enabled = true) {
  return useQuery<SidingStatusData>({
    queryKey: ['sidingStatus'],
    queryFn: () => fetchApi<SidingStatusData>('/network/sidings'),
    refetchInterval: enabled ? 4000 : false,
  });
}

export function useRunStressTest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (req: StressTestRequest = {}) =>
      fetchApi<StressTestResultData>('/simulation/stress-test', {
        method: 'POST',
        body: JSON.stringify({
          scenario_id: req.scenario_id || 'scenario_003',
          additional_delay_minutes: req.additional_delay_minutes || 0.0,
          enforce_siding_limits: req.enforce_siding_limits ?? true,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sidingStatus'] });
      queryClient.invalidateQueries({ queryKey: ['simulationStatus'] });
      queryClient.invalidateQueries({ queryKey: ['simulationKPIs'] });
    },
  });
}

// ─── Performance Analytics Hooks (RAIL-17) ──────────────────────────────────

export function useAnalyticsCompare(scenarioId = 'scenario_001') {
  return useQuery<AnalyticsComparisonData>({
    queryKey: ['analyticsCompare', scenarioId],
    queryFn: () => fetchApi<AnalyticsComparisonData>(`/analytics/compare?scenario_id=${scenarioId}`),
    staleTime: 30000,
  });
}

export function useAnalyticsSummary(scenarioId?: string) {
  const url = scenarioId ? `/analytics/summary?scenario_id=${scenarioId}` : '/analytics/summary';
  return useQuery<AnalyticsSummaryData>({
    queryKey: ['analyticsSummary', scenarioId],
    queryFn: () => fetchApi<AnalyticsSummaryData>(url),
    refetchInterval: 5000,
  });
}

export function useAnalyticsRuns(limit = 20, scenarioId?: string) {
  const queryParams = new URLSearchParams();
  queryParams.append('limit', limit.toString());
  if (scenarioId) queryParams.append('scenario_id', scenarioId);

  return useQuery<{ runs: AnalyticsRunRecord[]; total: number }>({
    queryKey: ['analyticsRuns', limit, scenarioId],
    queryFn: () => fetchApi<{ runs: AnalyticsRunRecord[]; total: number }>(`/analytics/runs?${queryParams.toString()}`),
    refetchInterval: 5000,
  });
}

export function useTriggerComparison() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (scenarioId: string = 'scenario_001') =>
      fetchApi<AnalyticsComparisonData>('/simulation/compare', {
        method: 'POST',
        body: JSON.stringify({ scenario_id: scenarioId }),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(['analyticsCompare', data.scenario_id], data);
      queryClient.invalidateQueries({ queryKey: ['analyticsSummary'] });
      queryClient.invalidateQueries({ queryKey: ['analyticsRuns'] });
    },
  });
}

// ─── Dispatch Audit Log Inspector Hook (RAIL-18) ────────────────────────────

export function useAuditLog(limit = 50, category?: string, trainId?: string) {
  const queryParams = new URLSearchParams();
  queryParams.append('limit', limit.toString());
  if (category) queryParams.append('category', category);
  if (trainId) queryParams.append('train_id', trainId);

  return useQuery<{ entries: AuditLogEntry[]; total_returned: number }>({
    queryKey: ['auditLog', limit, category, trainId],
    queryFn: () => fetchApi<{ entries: AuditLogEntry[]; total_returned: number }>(`/analytics/audit-log?${queryParams.toString()}`),
    refetchInterval: 4000,
  });
}



