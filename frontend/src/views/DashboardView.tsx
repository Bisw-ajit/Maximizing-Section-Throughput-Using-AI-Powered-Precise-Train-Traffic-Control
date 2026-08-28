import React from 'react';
import { KpiBar } from '../components/dashboard/KpiBar';
import { NetworkMap } from '../components/dashboard/NetworkMap';
import { SimulationControls } from '../components/dashboard/SimulationControls';
import { useDigitalTwin, useSimulationEvents } from '../hooks/useRailData';
import { AlertCircle, Cpu, Layers } from 'lucide-react';
import './DashboardView.css';

export const DashboardView: React.FC = () => {
  const { data: twin } = useDigitalTwin();
  const { data: eventsData } = useSimulationEvents(10);

  return (
    <div className="dashboard-view">
      <KpiBar />

      <div className="dashboard-grid">
        <div className="main-map-section">
          <NetworkMap />
          <SimulationControls />
        </div>

        <div className="dashboard-sidebar">
          {/* AI Conflict Detection Panel (Skeleton in Phase 3) */}
          <div className="panel-card">
            <div className="panel-header">
              <span className="panel-title">
                <AlertCircle size={16} className="icon-alert" /> Conflict Monitor
              </span>
              <span className="badge-ai">AI Layer Phase 2</span>
            </div>
            <div className="panel-body">
              {twin?.trains.some((t: any) => t.delay_minutes > 0) ? (
                <div className="conflict-card-preview">
                  <div className="conflict-meta">
                    <span className="severity-badge critical">CRITICAL</span>
                    <span className="conflict-loc">KUR Junction</span>
                  </div>
                  <p className="conflict-desc">
                    Crossing conflict detected on single-track section KUR-PURI between Puri Express (12837) & Rajdhani (22812).
                  </p>
                  <div className="ai-placeholder-note">
                    <Cpu size={14} /> Full AI optimization wired in Phase 2
                  </div>
                </div>
              ) : (
                <div className="empty-panel">No conflicts predicted in active scenario.</div>
              )}
            </div>
          </div>

          {/* Real-time Digital Twin Events Feed */}
          <div className="panel-card flex-1">
            <div className="panel-header">
              <span className="panel-title">
                <Layers size={16} /> Twin Live Stream
              </span>
              <span className="badge-live">LIVE</span>
            </div>
            <div className="panel-body events-list">
              {eventsData?.events && eventsData.events.length > 0 ? (
                eventsData.events.map((ev: any, i: number) => (
                  <div key={i} className="event-item">
                    <span className="event-time">+{ev.tick.toFixed(1)}m</span>
                    <span className={`event-type ${ev.type.toLowerCase()}`}>{ev.type}</span>
                    <span className="event-detail">
                      Train {ev.train_id} {ev.section_id || ev.node_id || ''}
                    </span>
                  </div>
                ))
              ) : (
                <div className="empty-panel">Start simulation to stream events.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
