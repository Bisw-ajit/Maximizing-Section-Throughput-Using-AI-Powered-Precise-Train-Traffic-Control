import React from 'react';
import { useScenarios, useScenarioActions, useSimulationKPIs } from '../hooks/useRailData';
import { useAppStore } from '../stores/useAppStore';
import { Play, CheckCircle2 } from 'lucide-react';
import './ScenariosView.css';

export const ScenariosView: React.FC = () => {
  const { data: scenariosData } = useScenarios();
  const { loadScenario } = useScenarioActions();
  const { activeScenarioId, setActiveScenarioId } = useAppStore();
  const { data: kpis } = useSimulationKPIs();

  const handleLoad = (id: string) => {
    setActiveScenarioId(id);
    loadScenario.mutate(id);
  };

  return (
    <div className="scenarios-view">
      <div className="view-header">
        <h2>Scenario Management & Benchmark Runs</h2>
        <p className="subtitle">Select and test baseline vs conflict scenarios for performance comparison.</p>
      </div>

      <div className="scenarios-grid">
        {scenariosData?.scenarios.map((scenario) => {
          const isActive = activeScenarioId === scenario.scenario_id;

          return (
            <div key={scenario.scenario_id} className={`scenario-card ${isActive ? 'active' : ''}`}>
              <div className="scenario-top">
                <span className="scenario-id">{scenario.scenario_id}</span>
                <span className={`diff-tag ${scenario.difficulty.toLowerCase()}`}>
                  {scenario.difficulty}
                </span>
              </div>

              <h3>{scenario.name}</h3>
              <p className="scenario-desc">{scenario.description}</p>

              <div className="scenario-stats">
                <span>🚆 {scenario.train_count} Trains</span>
                <span>📍 Network: {scenario.network_id}</span>
              </div>

              <div className="scenario-actions">
                {isActive ? (
                  <span className="loaded-badge">
                    <CheckCircle2 size={16} /> Currently Active
                  </span>
                ) : (
                  <button className="btn-load" onClick={() => handleLoad(scenario.scenario_id)}>
                    <Play size={14} /> Load Scenario
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="comparison-section">
        <h3>Scenario KPI Baseline Benchmarking</h3>
        <table className="kpi-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Current Run (Baseline FCFS)</th>
              <th>AI-Assisted Target (Phase 2)</th>
              <th>Target Improvement</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Throughput (Completed Trains)</td>
              <td>{kpis?.throughput || 0} trains</td>
              <td>5 trains</td>
              <td className="text-good">+25%</td>
            </tr>
            <tr>
              <td>Average Delay</td>
              <td>{kpis?.average_delay || 0} min</td>
              <td>2.1 min</td>
              <td className="text-good">↓ 40%</td>
            </tr>
            <tr>
              <td>Total Waiting Time</td>
              <td>{kpis?.waiting_time || 0} min</td>
              <td>4.0 min</td>
              <td className="text-good">↓ 55%</td>
            </tr>
            <tr>
              <td>Section Utilization</td>
              <td>{((kpis?.utilization || 0) * 100).toFixed(0)}%</td>
              <td>92%</td>
              <td className="text-good">+12%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
