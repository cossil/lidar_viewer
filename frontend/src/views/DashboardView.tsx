import React, { useEffect, useState } from 'react';
import { Play, Cpu, Layers, FileText, CheckCircle2, ArrowRight } from 'lucide-react';
import { api } from '../api/client';
import { MetricCard } from '../components/common/MetricCard';
import type { NavTab } from '../components/layout/Sidebar';

interface DashboardViewProps {
  onNavigate: (tab: NavTab) => void;
  onRunCanonical: () => void;
  isRunningCanonical?: boolean;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigate,
  onRunCanonical,
  isRunningCanonical,
}) => {
  const [sensorCount, setSensorCount] = useState(0);
  const [scenarioCount, setScenarioCount] = useState(0);

  useEffect(() => {
    const fetchCounts = async () => {
      try {
        const sensors = await api.listSensors();
        setSensorCount(sensors.length);
        const scenarios = await api.listScenarios();
        setScenarioCount(scenarios.length);
      } catch (err) {
        console.error('Error fetching dashboard counts', err);
      }
    };
    fetchCounts();
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-panel p-6 bg-gradient-to-r from-slate-900/90 via-cyan-950/20 to-indigo-950/20 border-cyan-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="badge badge-cyan">SilvaLab Forest Inventory Suite</span>
            <span className="text-xs text-slate-400 font-mono">v0.1.0-RC</span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            LiDAR Performance Analysis & Simulation Platform
          </h2>
          <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
            Physics-grounded simulation engine modeling mechanical spinning, structured raster, and non-repetitive scanners
            against forest targets with Monte Carlo uncertainty propagation and SI unit precision.
          </p>
        </div>

        <button
          onClick={onRunCanonical}
          disabled={isRunningCanonical}
          className="btn-primary shrink-0 text-sm px-5 py-3"
        >
          <Play className="w-4 h-4 fill-current" />
          {isRunningCanonical ? 'Executing Canonical Sim...' : 'Run Canonical Scenario (PRD §81)'}
        </button>
      </div>

      {/* Quick Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Sensor Models"
          value={sensorCount || 1}
          subtext="Versioned & provenance-tracked"
          status="info"
          thresholdText="Rule 9 Immutable"
        />
        <MetricCard
          label="Test Scenarios"
          value={scenarioCount || 1}
          subtext="Cylinder DBH & Box targets"
          status="info"
          thresholdText="PRD §13"
        />
        <MetricCard
          label="Simulation Modes"
          value="3"
          subtext="Monte Carlo, Analytical, Point Cloud"
          status="success"
          thresholdText="PRD §54"
        />
        <MetricCard
          label="Persistence"
          value="JSON Files"
          subtext="data/ with .latest pointers"
          status="success"
          thresholdText="D008 Compliant"
        />
      </div>

      {/* Canonical Fixture Card */}
      <div className="glass-panel p-6 border-white/10 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Canonical Reference Benchmark (PRD §81)</h3>
              <p className="text-xs text-slate-400">Standard test case specified for baseline validation</p>
            </div>
          </div>

          <span className="badge badge-emerald">10,000 MC Trials</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-900/60 p-4 rounded-xl border border-white/5 text-xs">
          <div>
            <span className="text-slate-500 block">Target Type</span>
            <span className="text-slate-200 font-semibold font-mono">Cylinder (Tree Trunk)</span>
          </div>
          <div>
            <span className="text-slate-500 block">DBH (Diameter)</span>
            <span className="text-slate-200 font-semibold font-mono">10.0 cm (0.10 m)</span>
          </div>
          <div>
            <span className="text-slate-500 block">Target Distance</span>
            <span className="text-slate-200 font-semibold font-mono">30.0 meters</span>
          </div>
          <div>
            <span className="text-slate-500 block">Target Reflectivity</span>
            <span className="text-slate-200 font-semibold font-mono">30% (ρ = 0.30)</span>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-slate-400">
            Simulates 1-second scan duration, calculating P(Detection), P(Reliable), P(Characterized), geometric coverage, and range uncertainty.
          </p>

          <button
            onClick={() => onNavigate('simulations')}
            className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
          >
            Open Simulations Console <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Modules Shortcuts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div
          onClick={() => onNavigate('sensors')}
          className="glass-panel p-5 cursor-pointer glass-panel-hover group"
        >
          <div className="flex items-center justify-between mb-3">
            <Cpu className="w-6 h-6 text-cyan-400 group-hover:scale-110 transition-transform" />
            <span className="badge badge-cyan text-[10px]">Inspect</span>
          </div>
          <h4 className="text-sm font-bold text-white mb-1">Sensor Library</h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            Manage LiDAR models with parameter-level provenance, PDF datasheet extraction, and immutable versioning.
          </p>
        </div>

        <div
          onClick={() => onNavigate('scenarios')}
          className="glass-panel p-5 cursor-pointer glass-panel-hover group"
        >
          <div className="flex items-center justify-between mb-3">
            <Layers className="w-6 h-6 text-indigo-400 group-hover:scale-110 transition-transform" />
            <span className="badge badge-indigo text-[10px]">Configure</span>
          </div>
          <h4 className="text-sm font-bold text-white mb-1">Scenario Builder</h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            Construct forest geometries: define DBH, cylindrical trunks, sensor pitch/yaw, and atmospheric scattering.
          </p>
        </div>

        <div
          onClick={() => onNavigate('reports')}
          className="glass-panel p-5 cursor-pointer glass-panel-hover group"
        >
          <div className="flex items-center justify-between mb-3">
            <FileText className="w-6 h-6 text-emerald-400 group-hover:scale-110 transition-transform" />
            <span className="badge badge-emerald text-[10px]">Export</span>
          </div>
          <h4 className="text-sm font-bold text-white mb-1">Engineering Reports</h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            Generate formal 14-section Markdown reports with full assumption registries and CSV data downloads.
          </p>
        </div>
      </div>
    </div>
  );
};
