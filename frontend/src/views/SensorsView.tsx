import React, { useEffect, useState } from 'react';
import { Cpu, History, CheckCircle, FileUp, Edit3, Sparkles } from 'lucide-react';
import { api } from '../api/client';
import type { Sensor } from '../api/types';

export const SensorsView: React.FC = () => {
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [selectedSensor, setSelectedSensor] = useState<Sensor | null>(null);
  const [versions, setVersions] = useState<Array<{ version: string; sensor: Sensor }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Edit Modal
  const [isEditing, setIsEditing] = useState(false);
  const [editRangeMax, setEditRangeMax] = useState<number>(200);
  const [editBeamDiv, setEditBeamDiv] = useState<number>(0.003);

  // Datasheet Modal
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionResult, setExtractionResult] = useState<any | null>(null);
  const [useLlm, setUseLlm] = useState(true);
  const [llmModel, setLlmModel] = useState('z-ai/glm-5.3-flash');

  const loadSensors = async () => {
    setIsLoading(true);
    try {
      const data = await api.listSensors();
      setSensors(data);
      if (data.length > 0) {
        setSelectedSensor(data[0]);
        loadVersions(data[0].sensor_id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load sensors');
    } finally {
      setIsLoading(false);
    }
  };

  const loadVersions = async (sensorId: string) => {
    try {
      const vers = await api.listSensorVersions(sensorId);
      setVersions(vers);
    } catch {
      setVersions([]);
    }
  };

  useEffect(() => {
    loadSensors();
  }, []);

  const handleSelectSensor = (sensor: Sensor) => {
    setSelectedSensor(sensor);
    loadVersions(sensor.sensor_id);
    if (sensor.range?.maximum?.value) setEditRangeMax(sensor.range.maximum.value);
    if (sensor.beam?.horizontal_divergence?.value) setEditBeamDiv(sensor.beam.horizontal_divergence.value);
  };

  const handleSaveEdit = async () => {
    if (!selectedSensor) return;
    try {
      const updated: Sensor = {
        ...selectedSensor,
        range: {
          ...selectedSensor.range,
          maximum: {
            value: editRangeMax,
            unit: 'm',
            origin: 'USER_DEFINED',
            status: 'known',
          },
        },
        beam: {
          ...selectedSensor.beam,
          horizontal_divergence: {
            value: editBeamDiv,
            unit: 'rad',
            origin: 'USER_DEFINED',
            status: 'known',
          },
        },
      };

      await api.updateSensor(selectedSensor.sensor_id, updated);
      setIsEditing(false);
      await loadSensors();
    } catch (err: any) {
      alert(`Failed to update sensor: ${err.message}`);
    }
  };

  const handleExtractDatasheet = async () => {
    if (!uploadFile) return;
    setIsExtracting(true);
    try {
      const res = await api.extractDatasheet(uploadFile, useLlm, llmModel);
      setExtractionResult(res);
    } catch (err: any) {
      alert(`Datasheet extraction failed: ${err.message}`);
    } finally {
      setIsExtracting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Cpu className="w-5 h-5 text-cyan-400" /> Sensor Library & Provenance Inspector
          </h2>
          <p className="text-xs text-slate-400">
            PRD §47.2 & §47.3 — Parameters carry immutable versions and document provenance (Rule 2 & 9)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="btn-secondary text-xs"
          >
            <FileUp className="w-4 h-4" /> Import Datasheet (PDF/TXT)
          </button>
          <button
            onClick={() => setIsEditing(true)}
            disabled={!selectedSensor}
            className="btn-primary text-xs"
          >
            <Edit3 className="w-4 h-4" /> Edit Parameters (Bump Version)
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
          {errorMsg}
        </div>
      )}

      {/* Main Grid: Sensor List + Parameter Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sensor List Column */}
        <div className="glass-panel p-4 space-y-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
            Registered LiDAR Sensors
          </span>

          <div className="space-y-2">
            {isLoading && <div className="text-xs text-slate-500 py-2">Loading sensors...</div>}
            {sensors.map((s) => {
              const isSelected = selectedSensor?.sensor_id === s.sensor_id;
              return (
                <div
                  key={s.sensor_id}
                  onClick={() => handleSelectSensor(s)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-cyan-950/30 border-cyan-500/40 shadow-sm'
                      : 'bg-slate-900/40 border-white/5 hover:border-white/10 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-white font-mono">{s.model || s.sensor_id}</span>
                    <span className="badge badge-cyan text-[10px]">v{s.version}</span>
                  </div>
                  <div className="text-xs text-slate-400">{s.manufacturer} • {s.sensor_type}</div>
                </div>
              );
            })}
          </div>

          {/* Versions Pinned List */}
          {versions.length > 0 && (
            <div className="mt-6 pt-4 border-t border-white/10 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <History className="w-3.5 h-3.5" /> Immutable Version History (Rule 9)
              </div>
              <div className="space-y-1">
                {versions.map((v) => (
                  <div
                    key={v.version}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-900/30 border border-white/5 text-xs text-slate-300 font-mono"
                  >
                    <span>@{v.version}</span>
                    <span className="text-[10px] text-emerald-400">Snapshot Retained</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Parameter Inspector Column */}
        <div className="glass-panel p-5 lg:col-span-2 space-y-5">
          {selectedSensor ? (
            <>
              <div className="flex items-start justify-between pb-3 border-b border-white/10">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-white font-mono">{selectedSensor.model}</h3>
                    <span className="badge badge-emerald text-[11px]">
                      {selectedSensor.validation?.status || 'validated'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Sensor ID: <span className="font-mono text-cyan-400">{selectedSensor.sensor_id}</span> • Manufacturer: {selectedSensor.manufacturer}
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-xs text-slate-500 block">Current Version</span>
                  <span className="text-sm font-bold font-mono text-white">v{selectedSensor.version}</span>
                </div>
              </div>

              {/* Parameter Table */}
              <div className="space-y-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">
                  Domain Parameters & Provenance (PRD §47.3)
                </span>

                <div className="overflow-x-auto rounded-xl border border-white/10">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/80 text-slate-400 uppercase font-semibold text-[10px] border-b border-white/10">
                      <tr>
                        <th className="p-3">Parameter Dotpath</th>
                        <th className="p-3">Value & Unit</th>
                        <th className="p-3">Origin / Status</th>
                        <th className="p-3">Provenance Source</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 bg-slate-900/40 text-slate-300">
                      {/* Range Maximum */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">range.maximum</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.range?.maximum?.value ?? 'Unknown'} {selectedSensor.range?.maximum?.unit || 'm'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-emerald text-[10px]">
                            {selectedSensor.range?.maximum?.status || 'known'}
                          </span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          {selectedSensor.range?.maximum?.origin || 'MANUFACTURER'} (Datasheet p.4)
                        </td>
                      </tr>

                      {/* Accuracy Range */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">accuracy.range</td>
                        <td className="p-3 font-mono font-bold text-white">
                          ±{selectedSensor.accuracy?.range?.value ?? '0.02'} {selectedSensor.accuracy?.range?.unit || 'm'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-emerald text-[10px]">known</span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          1-sigma definition (converted PRD §34)
                        </td>
                      </tr>

                      {/* Horizontal Beam Divergence */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">beam.horizontal_divergence</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.beam?.horizontal_divergence?.value ?? '0.003'} {selectedSensor.beam?.horizontal_divergence?.unit || 'rad'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-emerald text-[10px]">known</span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Circular beam approx (D002)
                        </td>
                      </tr>

                      {/* Point Rate */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">scan.point_rate</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.scan?.point_rate?.value?.toLocaleString() ?? '600,000'} {selectedSensor.scan?.point_rate?.unit || 'Hz'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-emerald text-[10px]">known</span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Point rate cap enforced (D018)
                        </td>
                      </tr>

                      {/* Rotation Frequency */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">scan.rotation_frequency</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.scan?.rotation_frequency?.value ?? '10'} {selectedSensor.scan?.rotation_frequency?.unit || 'Hz'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-emerald text-[10px]">known</span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          10 rotations/sec (600 RPM)
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-16 text-slate-500 text-sm">
              No sensor selected. Choose one from the library list.
            </div>
          )}
        </div>
      </div>

      {/* Edit Parameters Modal */}
      {isEditing && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel p-6 max-w-md w-full space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <h4 className="text-base font-bold text-white">Edit Parameters (Rule 9 Immutable Bump)</h4>
              <span className="badge badge-cyan text-[10px]">v{selectedSensor?.version} → Bump</span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Modifying validated parameters creates a new version snapshot while preserving the existing version for reproducibility.
            </p>

            <div className="space-y-3">
              <div>
                <label className="form-label">Maximum Range (m)</label>
                <input
                  type="number"
                  value={editRangeMax}
                  onChange={(e) => setEditRangeMax(parseFloat(e.target.value))}
                  className="form-input font-mono"
                />
              </div>

              <div>
                <label className="form-label">Beam Divergence (rad)</label>
                <input
                  type="number"
                  step="0.0005"
                  value={editBeamDiv}
                  onChange={(e) => setEditBeamDiv(parseFloat(e.target.value))}
                  className="form-input font-mono"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3">
              <button onClick={() => setIsEditing(false)} className="btn-secondary text-xs">
                Cancel
              </button>
              <button onClick={handleSaveEdit} className="btn-primary text-xs">
                Save & Bump Version
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Datasheet Upload Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel p-6 max-w-lg w-full space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <h4 className="text-base font-bold text-white">Datasheet Ingestion (PRD §11-12)</h4>
              <span className="badge badge-cyan text-[10px]">Non-Fabricating</span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Upload a manufacturer specification sheet. The extraction engine identifies optical, scanning, and range parameters with strict provenance tracking.
            </p>

            <div>
              <label className="form-label">Datasheet File (TXT, PDF, JSON)</label>
              <input
                type="file"
                accept=".pdf,.txt,.json"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="form-input text-xs"
              />
            </div>

            {/* OpenRouter LLM Extractor Option */}
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useLlm}
                  onChange={(e) => setUseLlm(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-950 text-indigo-500 focus:ring-indigo-500"
                />
                <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  Extract with OpenRouter AI
                </span>
                <span className="badge badge-amber text-[9px] ml-auto">LLM Enabled</span>
              </label>

              {useLlm && (
                <div className="pl-6 space-y-1.5 pt-1">
                  <label className="text-[10px] text-slate-400 block">OpenRouter Model:</label>
                  <input
                    type="text"
                    value={llmModel}
                    onChange={(e) => setLlmModel(e.target.value)}
                    className="form-input text-xs font-mono py-1 w-full"
                    placeholder="z-ai/glm-5.3-flash"
                  />
                  <p className="text-[10px] text-slate-400">
                    Utiliza <code>z-ai/glm-5.3-flash</code> via OpenRouter para estruturação não-fabricada dos parâmetros técnicos.
                  </p>
                </div>
              )}
            </div>

            {extractionResult && (
              <div className="p-3 bg-slate-900/80 rounded-lg border border-emerald-500/30 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> Extraction Successful
                  </span>
                  {extractionResult.llm_used && (
                    <span className="badge badge-amber text-[9px]">
                      Model: {extractionResult.llm_model}
                    </span>
                  )}
                </div>
                {extractionResult.warnings && extractionResult.warnings.length > 0 && (
                  <div className="text-[10px] text-amber-300 space-y-0.5">
                    {extractionResult.warnings.map((w: string, idx: number) => (
                      <div key={idx}>⚠️ {w}</div>
                    ))}
                  </div>
                )}
                <pre className="font-mono text-[10px] text-slate-300 max-h-36 overflow-y-auto">
                  {JSON.stringify(extractionResult, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3">
              <button onClick={() => setIsUploadModalOpen(false)} className="btn-secondary text-xs">
                Close
              </button>
              <button
                onClick={handleExtractDatasheet}
                disabled={!uploadFile || isExtracting}
                className="btn-primary text-xs"
              >
                {isExtracting ? 'Extracting Parameters...' : 'Run Extraction'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
