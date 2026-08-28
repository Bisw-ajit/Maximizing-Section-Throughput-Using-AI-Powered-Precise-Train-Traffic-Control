import React from 'react';
import { useTrainDetail } from '../../hooks/useRailData';
import { useAppStore } from '../../stores/useAppStore';
import { X, TrainFront, MapPin, Clock, Cpu } from 'lucide-react';
import './TrainDetailDrawer.css';

export const TrainDetailDrawer: React.FC = () => {
  const { selectedTrainId, setSelectedTrainId } = useAppStore();
  const { data: train } = useTrainDetail(selectedTrainId);

  if (!selectedTrainId || !train) return null;

  return (
    <div className="drawer-backdrop" onClick={() => setSelectedTrainId(null)}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div className="drawer-title">
            <TrainFront size={20} className="brand-icon" />
            <div>
              <h3>{train.name}</h3>
              <span className="train-number-tag">#{train.train_number}</span>
            </div>
          </div>
          <button className="btn-close" onClick={() => setSelectedTrainId(null)}>
            <X size={18} />
          </button>
        </div>

        <div className="drawer-content">
          <div className="info-block">
            <span className="block-label">Operational Status</span>
            <span className={`status-badge ${train.status.toLowerCase()}`}>{train.status}</span>
          </div>

          <div className="info-grid">
            <div className="info-cell">
              <span className="cell-label"><MapPin size={14} /> Current Node</span>
              <span className="cell-value">{train.current_node || 'En-route'}</span>
            </div>

            <div className="info-cell">
              <span className="cell-label"><Clock size={14} /> Running Delay</span>
              <span className={`cell-value ${train.delay_minutes > 0 ? 'text-delay' : ''}`}>
                {train.delay_minutes.toFixed(1)} minutes
              </span>
            </div>
          </div>

          <div className="info-block">
            <span className="block-label">Route Progress</span>
            <div className="drawer-progress-bar">
              <div
                className="drawer-progress-fill"
                style={{ width: `${(train.journey_progress || 0) * 100}%` }}
              />
            </div>
            <span className="progress-text">{((train.journey_progress || 0) * 100).toFixed(0)}% Journey Completed</span>
          </div>

          <div className="info-block ai-insights">
            <span className="block-label"><Cpu size={14} /> AI Decision Engine Insights (Phase 2)</span>
            <p className="ai-insight-text">
              Priority level {train.priority}. No headway violations detected for section entry.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
