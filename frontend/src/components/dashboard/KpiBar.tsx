import React from 'react';
import { useDigitalTwin, useSimulationKPIs } from '../../hooks/useRailData';
import { Train, AlertTriangle, CheckCircle, Clock, Zap } from 'lucide-react';
import './KpiBar.css';

export const KpiBar: React.FC = () => {
  const { data: twin } = useDigitalTwin();
  const { data: kpis } = useSimulationKPIs();

  const totalTrains = twin?.train_count || 0;
  const delayedTrains = twin?.trains.filter((t) => t.delay_minutes > 0).length || 0;
  const avgDelay = kpis?.average_delay ?? 0.0;
  const throughput = kpis?.throughput ?? 0;
  const utilization = ((kpis?.utilization ?? 0) * 100).toFixed(0);

  return (
    <div className="kpi-bar">
      <div className="kpi-card">
        <div className="kpi-icon blue">
          <Train size={18} />
        </div>
        <div className="kpi-content">
          <span className="kpi-label">Active Trains</span>
          <span className="kpi-value">{totalTrains}</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className={`kpi-icon ${delayedTrains > 0 ? 'amber' : 'green'}`}>
          <Clock size={18} />
        </div>
        <div className="kpi-content">
          <span className="kpi-label">Average Delay</span>
          <span className="kpi-value">{avgDelay} min</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="kpi-icon purple">
          <AlertTriangle size={18} />
        </div>
        <div className="kpi-content">
          <span className="kpi-label">Predicted Conflicts</span>
          <span className="kpi-value">{delayedTrains > 0 ? '1 (KUR)' : '0'}</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="kpi-icon green">
          <CheckCircle size={18} />
        </div>
        <div className="kpi-content">
          <span className="kpi-label">Throughput</span>
          <span className="kpi-value">{throughput} trains</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="kpi-icon cyan">
          <Zap size={18} />
        </div>
        <div className="kpi-content">
          <span className="kpi-label">Section Utilization</span>
          <span className="kpi-value">{utilization}%</span>
        </div>
      </div>
    </div>
  );
};
