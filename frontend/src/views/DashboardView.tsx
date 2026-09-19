import React from 'react';
import { KpiBar } from '../components/dashboard/KpiBar';
import { NetworkMap } from '../components/dashboard/NetworkMap';
import { SimulationControls } from '../components/dashboard/SimulationControls';
import { RecommendationPanel } from '../components/dashboard/RecommendationPanel';
import { useSimulationEvents } from '../hooks/useRailData';
import { Layers } from 'lucide-react';
import './DashboardView.css';

export const DashboardView: React.FC = () => {
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
          {/* Interactive AI Decision & Recommendation Panel (RAIL-11) */}
          <RecommendationPanel />

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
