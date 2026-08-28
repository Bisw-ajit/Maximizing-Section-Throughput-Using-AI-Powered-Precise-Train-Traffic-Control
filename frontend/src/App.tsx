import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './components/layout/Header';
import { DashboardView } from './views/DashboardView';
import { LiveTwinView } from './views/LiveTwinView';
import { ScenariosView } from './views/ScenariosView';
import { AnalyticsView } from './views/AnalyticsView';
import { TrainDetailDrawer } from './components/trains/TrainDetailDrawer';
import { useAppStore } from './stores/useAppStore';

const queryClient = new QueryClient();

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
        {activeTab === 'analytics' && <AnalyticsView />}
      </main>
      <TrainDetailDrawer />
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
