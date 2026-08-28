import React from 'react';
import { useSimulationKPIs } from '../hooks/useRailData';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import './AnalyticsView.css';

export const AnalyticsView: React.FC = () => {
  const { data: kpis } = useSimulationKPIs();

  const comparisonData = [
    { name: 'Throughput', Baseline: kpis?.throughput || 0, AIAssisted: 5 },
    { name: 'Avg Delay (min)', Baseline: kpis?.average_delay || 0, AIAssisted: 2.1 },
    { name: 'Waiting Time (min)', Baseline: kpis?.waiting_time || 0, AIAssisted: 4.0 },
  ];

  const trendData = [
    { time: '06:00', BaselineDelay: 0, AIDelay: 0 },
    { time: '06:15', BaselineDelay: 2, AIDelay: 0.5 },
    { time: '06:30', BaselineDelay: 8, AIDelay: 1.2 },
    { time: '06:45', BaselineDelay: 14, AIDelay: 2.0 },
    { time: '07:00', BaselineDelay: 12, AIDelay: 2.1 },
  ];

  return (
    <div className="analytics-view">
      <div className="view-header">
        <h2>Performance Analytics & KPI Optimization</h2>
        <p className="subtitle">Visualizing baseline vs AI-assisted section throughput and delay reductions.</p>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>KPI Comparison (Baseline vs AI-Assisted Target)</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="Baseline" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="AIAssisted" fill="#0284c7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-card">
          <h3>Delay Propagation Trend</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="BaselineDelay" stroke="#dc2626" strokeWidth={2} />
                <Line type="monotone" dataKey="AIDelay" stroke="#16a34a" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
