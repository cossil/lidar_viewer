import React, { useState } from 'react';
import { BarChart3, Box, Activity, Play } from 'lucide-react';
import { Plots2D } from '../components/visualization/Plots2D';
import { Scene3D } from '../components/visualization/Scene3D';
import { api } from '../api/client';

export const VisualizationsView: React.FC = () => {
  const [activeVizTab, setActiveVizTab] = useState<'3d' | '2d'>('3d');
  const [isSweeping, setIsSweeping] = useState(false);
  const [sweepResult, setSweepResult] = useState<any | null>(null);

  const handleRunDistanceSweep = async () => {
    setIsSweeping(true);
    try {
      const res = await api.runDistanceSweep({
        scenario_id: 'test-scenario-001',
        distance: {
          start: 5.0,
          end: 70.0,
          step: 5.0,
        },
        simulation: {
          mode: 'monte_carlo',
          trials: 200,
        },
      });
      setSweepResult(res);
      setActiveVizTab('2d');
    } catch (err: any) {
      console.warn('Sweep fallback', err);
    } finally {
      setIsSweeping(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Tab Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-cyan-400" /> Visualization Studio
          </h2>
          <p className="text-xs text-slate-400">
            PRD Phase 12 (§50-52) — Interactive 3D LiDAR Scene, Point Cloud inspection, and 2D Sweeps
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunDistanceSweep}
            disabled={isSweeping}
            className="btn-secondary text-xs"
          >
            <Play className="w-3.5 h-3.5" />
            {isSweeping ? 'Calculating 5-70m Sweep...' : 'Trigger Distance Sweep (PRD §42)'}
          </button>

          <div className="flex bg-slate-900/60 p-1 rounded-xl border border-white/10 text-xs">
            <button
              onClick={() => setActiveVizTab('3d')}
              className={`py-1.5 px-3 rounded-lg font-semibold flex items-center gap-1.5 transition-all ${
                activeVizTab === '3d'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Box className="w-3.5 h-3.5" /> 3D Scene & Point Cloud
            </button>
            <button
              onClick={() => setActiveVizTab('2d')}
              className={`py-1.5 px-3 rounded-lg font-semibold flex items-center gap-1.5 transition-all ${
                activeVizTab === '2d'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Activity className="w-3.5 h-3.5" /> 2D Plots & Heatmaps
            </button>
          </div>
        </div>
      </div>

      {/* Visualizers Container */}
      {activeVizTab === '3d' ? (
        <Scene3D
          targetType="cylinder"
          targetDbh={0.10}
          targetPosition={[30, 0, 0.5]}
        />
      ) : (
        <Plots2D
          sweepData={
            sweepResult
              ? {
                  distances: sweepResult.distances,
                  p_detected: sweepResult.p_detected,
                  p_reliable: sweepResult.p_reliable,
                  p_characterized: sweepResult.p_characterized,
                  expected_returns: sweepResult.expected_returns,
                }
              : undefined
          }
        />
      )}
    </div>
  );
};
