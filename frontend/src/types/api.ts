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
