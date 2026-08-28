import React from 'react';
import { useDigitalTwin } from '../hooks/useRailData';
import { useAppStore } from '../stores/useAppStore';
import { Radio, Search, MapPin, Clock, ArrowRight } from 'lucide-react';
import './LiveTwinView.css';

export const LiveTwinView: React.FC = () => {
  const { data: twin } = useDigitalTwin();
  const { setSelectedTrainId } = useAppStore();
  const [search, setSearch] = React.useState('');

  const trains = twin?.trains || [];
  const filteredTrains = trains.filter(
    (t) =>
      t.train_number.toLowerCase().includes(search.toLowerCase()) ||
      t.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="live-twin-view">
      <div className="twin-header">
        <div>
          <h2>Digital Twin — Active Trains</h2>
          <p className="subtitle">Real-time state tracking & telemetry across network corridors.</p>
        </div>

        <div className="search-box">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search by train number or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="trains-grid">
        {filteredTrains.map((train) => (
          <div
            key={train.train_id}
            className={`train-card priority-${train.priority}`}
            onClick={() => setSelectedTrainId(train.train_id)}
          >
            <div className="card-top">
              <div className="train-id-badge">
                <Radio size={14} />
                <span className="train-no">{train.train_number}</span>
              </div>
              <span className={`status-pill ${train.status.toLowerCase()}`}>{train.status}</span>
            </div>

            <h3 className="train-name">{train.name}</h3>

            <div className="card-details">
              <div className="detail-row">
                <MapPin size={14} />
                <span>Loc: <strong>{train.current_node || train.current_section || 'En-route'}</strong></span>
              </div>

              <div className="detail-row">
                <Clock size={14} />
                <span>Delay: <strong className={train.delay_minutes > 0 ? 'text-delay' : ''}>{train.delay_minutes.toFixed(1)} min</strong></span>
              </div>
            </div>

            <div className="progress-bar-container">
              <div
                className="progress-bar-fill"
                style={{ width: `${(train.journey_progress || 0) * 100}%` }}
              />
            </div>

            <div className="card-footer">
              <span className="source-tag">{train.data_source}</span>
              <span className="action-link">Inspect <ArrowRight size={12} /></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
