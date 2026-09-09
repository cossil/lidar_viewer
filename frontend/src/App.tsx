import React, { useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import type { NavTab } from './components/layout/Sidebar';
import { DashboardView } from './views/DashboardView';
import { SensorsView } from './views/SensorsView';
import { ScenariosView } from './views/ScenariosView';
import { SimulationsView } from './views/SimulationsView';
import { VisualizationsView } from './views/VisualizationsView';
import { ReportsView } from './views/ReportsView';
import { api } from './api/client';
import type { Scenario } from './api/types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('dashboard');
  const [isRunningCanonical, setIsRunningCanonical] = useState(false);

  const handleRunCanonical = async () => {
    setIsRunningCanonical(true);
    try {
      const scenario: Scenario = {
        scenario_id: 'canonical-prd-81',
        sensor_id: 'hesai-qt64',
        environment: { atmosphere: 'clear', vegetation: 'none' },
        sensor_pose: { position: [0, 0, 1.5], orientation: { yaw: 0, pitch: 0, roll: 0 } },
        target: {
          type: 'cylinder',
          diameter: 0.10, // 10 cm DBH
          position: [30.0, 0, 0.5],
          orientation: [0, 0, 1],
          reflectivity: 0.30, // 30%
        },
      };

      try {
        await api.createScenario(scenario);
      } catch {
        // May already exist
      }

      await api.createSimulation({
        scenario_id: 'canonical-prd-81',
        mode: 'monte_carlo',
        duration: 1.0,
        monte_carlo: { enabled: true, trials: 10000, random_seed: 123456 },
        detection_model_id: 'datasheet_envelope',
      });

      setCurrentTab('simulations');
    } catch (err: any) {
      console.warn('Canonical run error', err);
      setCurrentTab('simulations');
    } finally {
      setIsRunningCanonical(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Navbar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} />

        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {currentTab === 'dashboard' && (
              <DashboardView
                onNavigate={setCurrentTab}
                onRunCanonical={handleRunCanonical}
                isRunningCanonical={isRunningCanonical}
              />
            )}
            {currentTab === 'sensors' && <SensorsView />}
            {currentTab === 'scenarios' && <ScenariosView />}
            {currentTab === 'simulations' && <SimulationsView />}
            {currentTab === 'visualizations' && <VisualizationsView />}
            {currentTab === 'reports' && <ReportsView />}
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;
