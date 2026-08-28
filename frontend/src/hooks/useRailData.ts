import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from '../services/apiClient';
import { NetworkData, DigitalTwinState, Scenario, SimulationStatus, SimulationKPIs, SimulationEvent, Train } from '../types/api';

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
