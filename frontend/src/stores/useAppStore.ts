import { create } from 'zustand';

interface AppState {
  activeScenarioId: string | null;
  selectedTrainId: string | null;
  isSimulating: boolean;
  simulationSpeed: number;
  activeTab: 'dashboard' | 'trains' | 'scenarios' | 'conflicts' | 'analytics';
  isDemoMode: boolean;
  
  setActiveScenarioId: (id: string | null) => void;
  setSelectedTrainId: (id: string | null) => void;
  setIsSimulating: (simulating: boolean) => void;
  setSimulationSpeed: (speed: number) => void;
  setActiveTab: (tab: 'dashboard' | 'trains' | 'scenarios' | 'conflicts' | 'analytics') => void;
  setIsDemoMode: (val: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeScenarioId: 'scenario_001',
  selectedTrainId: null,
  isSimulating: false,
  simulationSpeed: 1.0,
  activeTab: 'dashboard',
  isDemoMode: false,

  setActiveScenarioId: (id) => set({ activeScenarioId: id }),
  setSelectedTrainId: (id) => set({ selectedTrainId: id }),
  setIsSimulating: (simulating) => set({ isSimulating: simulating }),
  setSimulationSpeed: (speed) => set({ simulationSpeed: speed }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setIsDemoMode: (val) => set({ isDemoMode: val }),
}));
