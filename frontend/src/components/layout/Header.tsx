import React from 'react';
import { useAppStore } from '../../stores/useAppStore';
import { Activity, ShieldAlert, Cpu, BarChart3, Radio, TrainFront } from 'lucide-react';
import './Header.css';

export const Header: React.FC = () => {
  const { activeTab, setActiveTab } = useAppStore();

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-icon">
          <TrainFront size={20} />
        </div>
        <div className="brand-text">
          <span className="brand-name">RAILOPTIX</span>
          <span className="brand-tagline">AI Traffic Decision System</span>
        </div>
      </div>

      <nav className="header-nav">
        <button
          className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <Activity size={16} />
          <span>Dashboard</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'trains' ? 'active' : ''}`}
          onClick={() => setActiveTab('trains')}
        >
          <Radio size={16} />
          <span>Live Twin</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'conflicts' ? 'active' : ''}`}
          onClick={() => setActiveTab('conflicts')}
        >
          <ShieldAlert size={16} />
          <span>Conflicts</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'scenarios' ? 'active' : ''}`}
          onClick={() => setActiveTab('scenarios')}
        >
          <Cpu size={16} />
          <span>Scenarios</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          <BarChart3 size={16} />
          <span>KPI Analytics</span>
        </button>
      </nav>

      <div className="header-status">
        <span className="status-indicator">
          <span className="status-dot"></span>
          <span className="status-text">Digital Twin Syncing</span>
        </span>
      </div>
    </header>
  );
};
