import React from 'react';
import { useSimulationStatus, useSimulationControlActions } from '../../hooks/useRailData';
import { Play, Pause, RotateCcw, FastForward } from 'lucide-react';
import './SimulationControls.css';

export const SimulationControls: React.FC = () => {
  const { data: status } = useSimulationStatus();
  const { startSimulation, pauseSimulation, resumeSimulation, resetSimulation, setSpeed } =
    useSimulationControlActions();

  const isRunning = status?.status === 'RUNNING';
  const isPaused = status?.status === 'PAUSED';
  const tick = status?.current_tick ? status.current_tick.toFixed(1) : '0.0';

  return (
    <div className="simulation-controls-bar">
      <div className="controls-group">
        {!isRunning && !isPaused ? (
          <button className="btn-primary" onClick={() => startSimulation.mutate()}>
            <Play size={16} /> Start Sim
          </button>
        ) : isRunning ? (
          <button className="btn-secondary" onClick={() => pauseSimulation.mutate()}>
            <Pause size={16} /> Pause
          </button>
        ) : (
          <button className="btn-primary" onClick={() => resumeSimulation.mutate()}>
            <Play size={16} /> Resume
          </button>
        )}

        <button className="btn-danger" onClick={() => resetSimulation.mutate()}>
          <RotateCcw size={16} /> Reset
        </button>
      </div>

      <div className="sim-speed-selector">
        <span className="speed-label"><FastForward size={14} /> Speed:</span>
        <button
          className={`speed-btn ${status?.speed_multiplier === 1 ? 'active' : ''}`}
          onClick={() => setSpeed.mutate(1.0)}
        >
          1x
        </button>
        <button
          className={`speed-btn ${status?.speed_multiplier === 2 ? 'active' : ''}`}
          onClick={() => setSpeed.mutate(2.0)}
        >
          2x
        </button>
        <button
          className={`speed-btn ${status?.speed_multiplier === 5 ? 'active' : ''}`}
          onClick={() => setSpeed.mutate(5.0)}
        >
          5x
        </button>
      </div>

      <div className="sim-clock">
        <span className="clock-label">Sim Time:</span>
        <span className="clock-value">{tick} min</span>
        <span className={`sim-badge ${status?.status?.toLowerCase() || 'idle'}`}>
          {status?.status || 'IDLE'}
        </span>
      </div>
    </div>
  );
};
