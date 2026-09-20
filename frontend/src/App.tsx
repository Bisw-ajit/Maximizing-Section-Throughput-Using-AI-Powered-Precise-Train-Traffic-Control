import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './components/layout/Header';
import { DashboardView } from './views/DashboardView';
import { LiveTwinView } from './views/LiveTwinView';
import { ScenariosView } from './views/ScenariosView';
import { AnalyticsView } from './views/AnalyticsView';
import { TrainDetailDrawer } from './components/trains/TrainDetailDrawer';
import { DemoController } from './components/demo/DemoController';
import { useAppStore } from './stores/useAppStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      throwOnError: false,   // never throw into React tree — handle via isError
    },
  },
});

// ── Simple Error Boundary so a crashed view never blanks the whole app ──────
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean; message: string }
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, message: '' };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, message: error.message };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '2rem', textAlign: 'center', color: '#64748b',
          background: '#f8fafc', borderRadius: '12px', margin: '2rem',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>⚠️</div>
          <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.5rem' }}>
            View failed to render
          </div>
          <div style={{ fontSize: '0.82rem', marginBottom: '1.25rem', color: '#94a3b8' }}>
            {this.state.message}
          </div>
          <button
            onClick={() => this.setState({ hasError: false, message: '' })}
            style={{
              padding: '0.45rem 1.2rem', borderRadius: '6px', border: 'none',
              background: '#0284c7', color: '#fff', cursor: 'pointer', fontSize: '0.85rem'
            }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export const AppContent: React.FC = () => {
  const { activeTab } = useAppStore();

  return (
    <div className="app-root">
      <Header />
      <main className="app-main">
        {activeTab === 'dashboard' && <DashboardView />}
        {activeTab === 'trains' && <LiveTwinView />}
        {activeTab === 'scenarios' && <ScenariosView />}
        {activeTab === 'conflicts' && <DashboardView />}
        {activeTab === 'analytics' && <ErrorBoundary><AnalyticsView /></ErrorBoundary>}
      </main>
      <TrainDetailDrawer />
      <DemoController />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
};

export default App;
