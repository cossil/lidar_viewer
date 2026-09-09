import React, { useEffect, useState } from 'react';
import { Layers, Save, Sliders, CheckCircle2, TreePine, Sun } from 'lucide-react';
import { api } from '../api/client';
import type { Scenario, Sensor } from '../api/types';

export const ScenariosView: React.FC = () => {
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedSensorId, setSelectedSensorId] = useState<string>('hesai-qt64');

  // Target Form state
  const [targetType, setTargetType] = useState<'cylinder' | 'box'>('cylinder');
  const [targetDbh, setTargetDbh] = useState<number>(0.10); // 10cm
  const [targetDist, setTargetDist] = useState<number>(30.0); // 30m
  const [targetZ, setTargetZ] = useState<number>(0.5);
  const [reflectivity, setReflectivity] = useState<number>(0.30); // 30%

  // Environment state
  const [atmosphere, setAtmosphere] = useState<'clear' | 'rain' | 'fog' | 'dust'>('clear');
  const [vegetation, setVegetation] = useState<'none' | 'sparse' | 'moderate' | 'dense'>('none');

  // LiDAR Pose
  const [sensorZ, setSensorZ] = useState<number>(1.5);
  const [sensorPitch, setSensorPitch] = useState<number>(0.0);

  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const sList = await api.listSensors();
        setSensors(sList);
        if (sList.length > 0) setSelectedSensorId(sList[0].sensor_id);
        const scList = await api.listScenarios();
        setScenarios(scList);
      } catch (err) {
        console.error(err);
      }
    };
    loadData();
  }, []);

  const handleSaveScenario = async () => {
    const scenarioData: Scenario = {
      scenario_id: `scenario-${Date.now().toString().slice(-6)}`,
      sensor_id: selectedSensorId,
      environment: {
        atmosphere,
        vegetation,
      },
      sensor_pose: {
        position: [0, 0, sensorZ],
        orientation: { yaw: 0, pitch: sensorPitch, roll: 0 },
      },
      target: {
        type: targetType,
        diameter: targetDbh,
        position: [targetDist, 0, targetZ],
        orientation: [0, 0, 1],
        reflectivity,
      },
    };

    try {
      await api.createScenario(scenarioData);
      setSaveStatus('Scenario saved successfully to data/scenarios/');
      const updated = await api.listScenarios();
      setScenarios(updated);
      setTimeout(() => setSaveStatus(null), 4000);
    } catch (err: any) {
      alert(`Failed to save scenario: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" /> Scenario Builder
          </h2>
          <p className="text-xs text-slate-400">
            PRD §48 — Define sensor pose, target geometry (DBH/cylinder), and atmospheric conditions
          </p>
        </div>

        <button onClick={handleSaveScenario} className="btn-primary text-xs">
          <Save className="w-4 h-4" /> Save Scenario to Disk
        </button>
      </div>

      {saveStatus && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" /> {saveStatus}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Target Configuration */}
        <div className="glass-panel p-5 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-white/10">
            <TreePine className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Forest Target Geometry
            </h3>
          </div>

          <div className="space-y-3">
            <div>
              <label className="form-label">Target Geometry Type</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setTargetType('cylinder')}
                  className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                    targetType === 'cylinder'
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      : 'bg-slate-900/50 text-slate-400 border-white/5'
                  }`}
                >
                  Cylinder (Tree Trunk)
                </button>
                <button
                  type="button"
                  onClick={() => setTargetType('box')}
                  className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                    targetType === 'box'
                      ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                      : 'bg-slate-900/50 text-slate-400 border-white/5'
                  }`}
                >
                  Box Geometry
                </button>
              </div>
            </div>

            {targetType === 'cylinder' && (
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="form-label m-0">Trunk DBH (Diameter at Breast Height)</label>
                  <span className="text-xs font-mono font-bold text-cyan-400">
                    {Math.round(targetDbh * 100)} cm ({targetDbh.toFixed(2)} m)
                  </span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="1.50"
                  step="0.05"
                  value={targetDbh}
                  onChange={(e) => setTargetDbh(parseFloat(e.target.value))}
                  className="w-full accent-cyan-400"
                />
              </div>
            )}

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="form-label m-0">Distance from LiDAR (+X axis)</label>
                <span className="text-xs font-mono font-bold text-cyan-400">{targetDist} meters</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                step="5"
                value={targetDist}
                onChange={(e) => setTargetDist(parseFloat(e.target.value))}
                className="w-full accent-cyan-400"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="form-label m-0">Target Reflectivity (ρ)</label>
                <span className="text-xs font-mono font-bold text-cyan-400">
                  {Math.round(reflectivity * 100)}% ({reflectivity.toFixed(2)})
                </span>
              </div>
              <input
                type="range"
                min="0.05"
                max="1.0"
                step="0.05"
                value={reflectivity}
                onChange={(e) => setReflectivity(parseFloat(e.target.value))}
                className="w-full accent-cyan-400"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="form-label m-0">Target Base Height Z (m)</label>
                <span className="text-xs font-mono font-bold text-cyan-400">{targetZ} m</span>
              </div>
              <input
                type="number"
                step="0.1"
                value={targetZ}
                onChange={(e) => setTargetZ(parseFloat(e.target.value))}
                className="form-input font-mono text-xs"
              />
            </div>
          </div>
        </div>

        {/* Center Column: LiDAR Pose & Sensor Selector */}
        <div className="glass-panel p-5 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-white/10">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              LiDAR Sensor & Mounting Pose
            </h3>
          </div>

          <div className="space-y-3">
            <div>
              <label className="form-label">Mounted LiDAR Sensor</label>
              <select
                value={selectedSensorId}
                onChange={(e) => setSelectedSensorId(e.target.value)}
                className="form-input font-mono text-xs"
              >
                {sensors.map((s) => (
                  <option key={s.sensor_id} value={s.sensor_id}>
                    {s.manufacturer} {s.model} (v{s.version})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="form-label">Mounting Height Z (meters above ground)</label>
              <input
                type="number"
                step="0.1"
                value={sensorZ}
                onChange={(e) => setSensorZ(parseFloat(e.target.value))}
                className="form-input font-mono text-xs"
              />
            </div>

            <div>
              <label className="form-label">Sensor Pitch Angle (radians)</label>
              <input
                type="number"
                step="0.05"
                value={sensorPitch}
                onChange={(e) => setSensorPitch(parseFloat(e.target.value))}
                className="form-input font-mono text-xs"
              />
            </div>

            <div className="p-3 bg-slate-900/60 rounded-xl border border-white/5 space-y-1 text-xs">
              <span className="text-slate-400 font-semibold block">Coordinate Convention (D001)</span>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Right-handed frame: +X points forward toward target, +Y points right, +Z points up.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Environment & Saved Scenarios */}
        <div className="glass-panel p-5 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-white/10">
            <Sun className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Environment & Weather
            </h3>
          </div>

          <div className="space-y-3">
            <div>
              <label className="form-label">Atmosphere Condition</label>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {(['clear', 'rain', 'fog', 'dust'] as const).map((atm) => (
                  <button
                    key={atm}
                    type="button"
                    onClick={() => setAtmosphere(atm)}
                    className={`py-2 px-2.5 rounded-lg font-medium border text-center capitalize ${
                      atmosphere === atm
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                        : 'bg-slate-900/50 text-slate-400 border-white/5'
                    }`}
                  >
                    {atm} {atm !== 'clear' && <span className="text-[10px] text-amber-400">*</span>}
                  </button>
                ))}
              </div>
              {atmosphere !== 'clear' && (
                <p className="text-[10px] text-amber-400/90 mt-1">
                  * PRD §48: Atmospheric scattering presets outside clear atmosphere are labeled for future calibration models.
                </p>
              )}
            </div>

            <div>
              <label className="form-label">Vegetation Density</label>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {(['none', 'sparse', 'moderate', 'dense'] as const).map((veg) => (
                  <button
                    key={veg}
                    type="button"
                    onClick={() => setVegetation(veg)}
                    className={`py-2 px-2.5 rounded-lg font-medium border text-center capitalize ${
                      vegetation === veg
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : 'bg-slate-900/50 text-slate-400 border-white/5'
                    }`}
                  >
                    {veg}
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-2 border-t border-white/10">
              <span className="form-label">Saved Scenarios in data/</span>
              <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                {scenarios.map((sc) => (
                  <div
                    key={sc.scenario_id}
                    className="p-2.5 rounded-lg bg-slate-900/40 border border-white/5 text-xs flex justify-between items-center"
                  >
                    <span className="font-mono text-slate-300">{sc.scenario_id}</span>
                    <span className="badge badge-emerald text-[10px]">
                      {sc.target.type} ({Math.round((sc.target.diameter || 0.1) * 100)}cm)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
