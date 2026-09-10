import React, { useEffect, useState } from 'react';
import {
  Cpu,
  History,
  CheckCircle,
  Edit3,
  Plus,
  Trash2,
  AlertTriangle,
  X,
  Sliders,
  Zap,
  Compass,
} from 'lucide-react';
import { api } from '../api/client';
import type { Sensor } from '../api/types';

interface SensorFormData {
  sensor_id: string;
  manufacturer: string;
  model: string;
  version: string;
  sensor_type: string;
  hardware_revision: string;
  firmware_version: string;
  // Range
  range_min: string;
  range_max: string;
  // Accuracy & Precision
  accuracy_range: string;
  precision_range: string;
  // Beam Optics
  wavelength: string;
  beam_h_div_mrad: string;
  beam_v_div_mrad: string;
  beam_shape: 'circular' | 'elliptical' | 'gaussian' | 'unknown';
  // Scan Dynamics
  point_rate: string;
  rotation_freq: string;
  frame_rate: string;
  channel_count: string;
  fov_horizontal: string;
  fov_vertical: string;
  validation_status: 'validated' | 'unvalidated' | 'provisional';
}

const initialFormData: SensorFormData = {
  sensor_id: '',
  manufacturer: '',
  model: '',
  version: '1.0.0',
  sensor_type: 'mechanical_spinning',
  hardware_revision: '',
  firmware_version: '',
  range_min: '1.0',
  range_max: '250.0',
  accuracy_range: '0.02',
  precision_range: '0.01',
  wavelength: '905',
  beam_h_div_mrad: '1.6',
  beam_v_div_mrad: '0.5',
  beam_shape: 'elliptical',
  point_rate: '600000',
  rotation_freq: '10',
  frame_rate: '10',
  channel_count: '1',
  fov_horizontal: '360',
  fov_vertical: '45',
  validation_status: 'validated',
};

export const SensorsView: React.FC = () => {
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [selectedSensor, setSelectedSensor] = useState<Sensor | null>(null);
  const [versions, setVersions] = useState<Array<{ version: string; sensor: Sensor }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form Modal (Create & Edit)
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [formActiveTab, setFormActiveTab] = useState<'identity' | 'range' | 'optics' | 'scan'>('identity');
  const [formData, setFormData] = useState<SensorFormData>(initialFormData);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Delete Modal
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadSensors = async (preserveSelectedId?: string) => {
    setIsLoading(true);
    try {
      const data = await api.listSensors();
      setSensors(data);
      if (data.length > 0) {
        const found = preserveSelectedId ? data.find((s) => s.sensor_id === preserveSelectedId) : null;
        const target = found || data[0];
        setSelectedSensor(target);
        loadVersions(target.sensor_id);
      } else {
        setSelectedSensor(null);
        setVersions([]);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Falha ao carregar sensores');
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
  };

  // Open Create Modal
  const handleOpenCreate = () => {
    setFormMode('create');
    setFormData({
      ...initialFormData,
      sensor_id: `sensor-${Date.now().toString().slice(-4)}`,
    });
    setFormActiveTab('identity');
    setFormError(null);
    setIsFormOpen(true);
  };

  // Open Edit Modal
  const handleOpenEdit = () => {
    if (!selectedSensor) return;
    setFormMode('edit');

    // Convert rad back to mrad for human readability in form
    const hDivMrad = selectedSensor.beam?.horizontal_divergence?.value != null
      ? (selectedSensor.beam.horizontal_divergence.value * 1000).toString()
      : '1.6';
    const vDivMrad = selectedSensor.beam?.vertical_divergence?.value != null
      ? (selectedSensor.beam.vertical_divergence.value * 1000).toString()
      : '0.5';

    setFormData({
      sensor_id: selectedSensor.sensor_id,
      manufacturer: selectedSensor.manufacturer || '',
      model: selectedSensor.model || '',
      version: selectedSensor.version || '1.0.0',
      sensor_type: selectedSensor.sensor_type || 'mechanical_spinning',
      hardware_revision: selectedSensor.hardware_revision || '',
      firmware_version: selectedSensor.firmware_version || '',
      range_min: selectedSensor.range?.minimum?.value != null ? selectedSensor.range.minimum.value.toString() : '',
      range_max: selectedSensor.range?.maximum?.value != null ? selectedSensor.range.maximum.value.toString() : '200',
      accuracy_range: selectedSensor.accuracy?.range?.value != null ? selectedSensor.accuracy.range.value.toString() : '0.02',
      precision_range: selectedSensor.precision?.range?.value != null ? selectedSensor.precision.range.value.toString() : '',
      wavelength: selectedSensor.wavelength?.value != null ? selectedSensor.wavelength.value.toString() : '905',
      beam_h_div_mrad: hDivMrad,
      beam_v_div_mrad: vDivMrad,
      beam_shape: (selectedSensor.beam?.beam_shape as any) || 'elliptical',
      point_rate: selectedSensor.scan?.point_rate?.value != null ? selectedSensor.scan.point_rate.value.toString() : '600000',
      rotation_freq: selectedSensor.scan?.rotation_frequency?.value != null ? selectedSensor.scan.rotation_frequency.value.toString() : '10',
      frame_rate: selectedSensor.scan?.frame_rate?.value != null ? selectedSensor.scan.frame_rate.value.toString() : '10',
      channel_count: selectedSensor.angular?.channel_count?.value != null
        ? selectedSensor.angular.channel_count.value.toString()
        : selectedSensor.scan?.channels != null ? selectedSensor.scan.channels.toString() : '1',
      fov_horizontal: selectedSensor.angular?.horizontal_fov?.value != null ? selectedSensor.angular.horizontal_fov.value.toString() : '360',
      fov_vertical: selectedSensor.angular?.vertical_fov?.value != null ? selectedSensor.angular.vertical_fov.value.toString() : '45',
      validation_status: (selectedSensor.validation?.status as any) || 'validated',
    });
    setFormActiveTab('identity');
    setFormError(null);
    setIsFormOpen(true);
  };

  // Submit Create or Edit
  const handleSubmitForm = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    // Form Validations
    if (!formData.sensor_id.trim()) {
      setFormError('Identificador do sensor (sensor_id) é obrigatório.');
      setFormActiveTab('identity');
      return;
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(formData.sensor_id.trim())) {
      setFormError('sensor_id deve conter apenas letras, números, hífens (-) ou sublinhados (_).');
      setFormActiveTab('identity');
      return;
    }
    if (!formData.manufacturer.trim()) {
      setFormError('Nome do fabricante é obrigatório.');
      setFormActiveTab('identity');
      return;
    }
    if (!formData.model.trim()) {
      setFormError('Modelo do sensor é obrigatório.');
      setFormActiveTab('identity');
      return;
    }
    const rangeMaxNum = parseFloat(formData.range_max);
    if (isNaN(rangeMaxNum) || rangeMaxNum <= 0) {
      setFormError('Alcance máximo (range.maximum) deve ser um número maior que zero.');
      setFormActiveTab('range');
      return;
    }
    const beamHDivNum = parseFloat(formData.beam_h_div_mrad);
    if (isNaN(beamHDivNum) || beamHDivNum <= 0) {
      setFormError('Divergência horizontal do feixe deve ser um número maior que zero.');
      setFormActiveTab('optics');
      return;
    }
    const pointRateNum = parseFloat(formData.point_rate);
    if (isNaN(pointRateNum) || pointRateNum <= 0) {
      setFormError('Taxa de pontos (point_rate) deve ser um número maior que zero.');
      setFormActiveTab('scan');
      return;
    }
    const rotationFreqNum = parseFloat(formData.rotation_freq);
    if (isNaN(rotationFreqNum) || rotationFreqNum <= 0) {
      setFormError('Frequência de rotação deve ser um número maior que zero.');
      setFormActiveTab('scan');
      return;
    }

    setIsSubmitting(true);
    try {
      const minRangeVal = formData.range_min.trim() ? parseFloat(formData.range_min) : null;
      const accRangeVal = formData.accuracy_range.trim() ? parseFloat(formData.accuracy_range) : null;
      const precRangeVal = formData.precision_range.trim() ? parseFloat(formData.precision_range) : null;
      const wavelengthVal = formData.wavelength.trim() ? parseFloat(formData.wavelength) : null;
      const beamVDivVal = formData.beam_v_div_mrad.trim() ? parseFloat(formData.beam_v_div_mrad) : null;
      const frameRateVal = formData.frame_rate.trim() ? parseFloat(formData.frame_rate) : null;
      const channelCountVal = formData.channel_count.trim() ? parseInt(formData.channel_count, 10) : null;
      const fovHVal = formData.fov_horizontal.trim() ? parseFloat(formData.fov_horizontal) : null;
      const fovVVal = formData.fov_vertical.trim() ? parseFloat(formData.fov_vertical) : null;

      // Construct Pydantic-compliant Sensor payload
      const payload: Sensor = {
        sensor_id: formMode === 'create' ? formData.sensor_id.trim() : (selectedSensor?.sensor_id || formData.sensor_id.trim()),
        manufacturer: formData.manufacturer.trim(),
        model: formData.model.trim(),
        version: formMode === 'create' ? (formData.version.trim() || '1.0.0') : (selectedSensor?.version || '1.0.0'),
        sensor_type: formData.sensor_type,
        hardware_revision: formData.hardware_revision.trim() || undefined,
        firmware_version: formData.firmware_version.trim() || undefined,
        wavelength: wavelengthVal != null ? {
          value: wavelengthVal,
          unit: 'nm',
          origin: 'USER_DEFINED',
          status: 'known',
        } : undefined,
        range: {
          minimum: minRangeVal != null ? {
            value: minRangeVal,
            unit: 'm',
            origin: 'USER_DEFINED',
            status: 'known',
          } : undefined,
          maximum: {
            value: rangeMaxNum,
            unit: 'm',
            origin: 'USER_DEFINED',
            status: 'known',
          },
          reflectivity_curves: selectedSensor?.range?.reflectivity_curves || [],
        },
        accuracy: accRangeVal != null ? {
          range: {
            value: accRangeVal,
            unit: 'm',
            origin: 'USER_DEFINED',
            status: 'known',
          },
        } : undefined,
        precision: precRangeVal != null ? {
          range: {
            value: precRangeVal,
            unit: 'm',
            origin: 'USER_DEFINED',
            status: 'known',
          },
        } : undefined,
        beam: {
          horizontal_divergence: {
            value: beamHDivNum / 1000.0, // convert mrad to rad
            unit: 'rad',
            origin: 'USER_DEFINED',
            status: 'known',
          },
          vertical_divergence: beamVDivVal != null ? {
            value: beamVDivVal / 1000.0,
            unit: 'rad',
            origin: 'USER_DEFINED',
            status: 'known',
          } : undefined,
          beam_shape: formData.beam_shape,
        },
        scan: {
          type: formData.sensor_type, // Must strictly match sensor_type per model validator
          point_rate: {
            value: pointRateNum,
            unit: 'Hz',
            origin: 'USER_DEFINED',
            status: 'known',
          },
          rotation_frequency: {
            value: rotationFreqNum,
            unit: 'Hz',
            origin: 'USER_DEFINED',
            status: 'known',
          },
          frame_rate: frameRateVal != null ? {
            value: frameRateVal,
            unit: 'Hz',
            origin: 'USER_DEFINED',
            status: 'known',
          } : undefined,
        },
        angular: {
          channel_count: channelCountVal != null ? {
            value: channelCountVal,
            unit: 'count',
            origin: 'USER_DEFINED',
            status: 'known',
          } : undefined,
          horizontal_fov: fovHVal != null ? {
            value: fovHVal,
            unit: 'deg',
            origin: 'USER_DEFINED',
            status: 'known',
          } : undefined,
          vertical_fov: fovVVal != null ? {
            value: fovVVal,
            unit: 'deg',
            origin: 'USER_DEFINED',
            status: 'known',
          } : undefined,
        },
        validation: {
          status: formData.validation_status || 'validated',
          validated_by: 'Manual User Form',
          validated_at: new Date().toISOString(),
        },
        assumptions: selectedSensor?.assumptions || [],
        provenance: selectedSensor?.provenance || [],
      };

      if (formMode === 'create') {
        await api.createSensor(payload);
        setSuccessMsg(`Sensor "${payload.model}" (${payload.sensor_id}) cadastrado com sucesso!`);
      } else {
        const res = await api.updateSensor(payload.sensor_id, payload);
        setSuccessMsg(`Sensor "${payload.model}" atualizado para v${res.version} (snapshot retido conforme Regra 9).`);
      }

      setIsFormOpen(false);
      await loadSensors(payload.sensor_id);
    } catch (err: any) {
      setFormError(err.message || 'Erro ao salvar sensor');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Sensor
  const handleDeleteSensor = async () => {
    if (!selectedSensor) return;
    setIsDeleting(true);
    try {
      await api.deleteSensor(selectedSensor.sensor_id);
      setSuccessMsg(`Sensor "${selectedSensor.model}" (${selectedSensor.sensor_id}) excluído com sucesso.`);
      setIsDeleteModalOpen(false);
      await loadSensors();
    } catch (err: any) {
      alert(`Falha ao excluir sensor: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Cpu className="w-5 h-5 text-cyan-400" /> Catálogo & Gerenciamento de Sensores LiDAR
          </h2>
          <p className="text-xs text-slate-400">
            Cadastro manual, edição de especificações com versionamento imutável e controle de acurácia física
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleOpenCreate}
            className="btn-primary text-xs flex items-center gap-1.5 shadow-lg shadow-cyan-950/40"
          >
            <Plus className="w-4 h-4" /> Cadastrar Novo Sensor
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" /> {successMsg}
          </span>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400/60 hover:text-emerald-300">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
          <span className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400" /> {errorMsg}
          </span>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400/60 hover:text-rose-300">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Grid: Sensor List + Parameter Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sensor List Column */}
        <div className="glass-panel p-4 space-y-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Sensores Disponíveis ({sensors.length})
            </span>
          </div>

          <div className="space-y-2">
            {isLoading && <div className="text-xs text-slate-500 py-2">Carregando catálogo...</div>}
            {sensors.map((s) => {
              const isSelected = selectedSensor?.sensor_id === s.sensor_id;
              return (
                <div
                  key={s.sensor_id}
                  onClick={() => handleSelectSensor(s)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-cyan-950/40 border-cyan-500/50 shadow-md ring-1 ring-cyan-500/20'
                      : 'bg-slate-900/40 border-white/5 hover:border-white/15 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-white font-mono">{s.model || s.sensor_id}</span>
                    <span className="badge badge-cyan text-[10px]">v{s.version}</span>
                  </div>
                  <div className="text-xs text-slate-400 flex items-center justify-between">
                    <span>{s.manufacturer}</span>
                    <span className="text-[11px] text-slate-500 font-mono">{s.sensor_type}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Versions Pinned List */}
          {versions.length > 0 && (
            <div className="mt-6 pt-4 border-t border-white/10 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <History className="w-3.5 h-3.5 text-cyan-400" /> Histórico de Snapshots (Regra 9)
              </div>
              <p className="text-[11px] text-slate-500">
                Snapshots imutáveis retidos para reprodução de simulações passadas.
              </p>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {versions.map((v) => (
                  <div
                    key={v.version}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-900/40 border border-white/5 text-xs text-slate-300 font-mono"
                  >
                    <span>@{v.version}</span>
                    <span className="text-[10px] text-emerald-400 font-sans">Retido</span>
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
              {/* Sensor Header Actions */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-white/10 gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-white font-mono">{selectedSensor.model}</h3>
                    <span className="badge badge-emerald text-[11px]">
                      {selectedSensor.validation?.status || 'validated'}
                    </span>
                    <span className="badge badge-cyan text-[11px]">
                      v{selectedSensor.version}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    ID: <span className="font-mono text-cyan-400 font-semibold">{selectedSensor.sensor_id}</span> • Fabricante: {selectedSensor.manufacturer}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleOpenEdit}
                    className="btn-secondary text-xs flex items-center gap-1.5"
                  >
                    <Edit3 className="w-3.5 h-3.5 text-cyan-400" /> Editar Parâmetros
                  </button>
                  <button
                    onClick={() => setIsDeleteModalOpen(true)}
                    className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 hover:bg-rose-500/20 hover:border-rose-500/50 transition-all"
                    title="Excluir este sensor"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Quick Specs Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Alcance Máx</span>
                  <div className="text-base font-bold font-mono text-white">
                    {selectedSensor.range?.maximum?.value ?? 'N/A'} <span className="text-xs font-normal text-slate-400">m</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Taxa de Pontos</span>
                  <div className="text-base font-bold font-mono text-white">
                    {selectedSensor.scan?.point_rate?.value != null ? (selectedSensor.scan.point_rate.value / 1000).toLocaleString() + 'k' : 'N/A'}{' '}
                    <span className="text-xs font-normal text-slate-400">pts/s</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Divergência Feixe</span>
                  <div className="text-base font-bold font-mono text-white">
                    {selectedSensor.beam?.horizontal_divergence?.value != null
                      ? (selectedSensor.beam.horizontal_divergence.value * 1000).toFixed(2)
                      : 'N/A'}{' '}
                    <span className="text-xs font-normal text-slate-400">mrad</span>
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Comprimento de Onda</span>
                  <div className="text-base font-bold font-mono text-white">
                    {selectedSensor.wavelength?.value ?? '905'} <span className="text-xs font-normal text-slate-400">nm</span>
                  </div>
                </div>
              </div>

              {/* Complete Parameter Table */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">
                    Parâmetros Físicos & Técnicos para Simulação
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Arquitetura: {selectedSensor.sensor_type}
                  </span>
                </div>

                <div className="overflow-x-auto rounded-xl border border-white/10">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/80 text-slate-400 uppercase font-semibold text-[10px] border-b border-white/10">
                      <tr>
                        <th className="p-3">Parâmetro</th>
                        <th className="p-3">Valor & Unidade</th>
                        <th className="p-3">Origem / Status</th>
                        <th className="p-3">Observações / Impacto</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 bg-slate-900/40 text-slate-300">
                      {/* Range Maximum */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">range.maximum</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.range?.maximum?.value ?? 'Desconhecido'} {selectedSensor.range?.maximum?.unit || 'm'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-emerald text-[10px]">
                            {selectedSensor.range?.maximum?.origin || 'USER_DEFINED'}
                          </span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Limite superior de alcance na simulação
                        </td>
                      </tr>

                      {/* Range Minimum */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">range.minimum</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.range?.minimum?.value ?? '0.5'} {selectedSensor.range?.minimum?.unit || 'm'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-cyan text-[10px]">
                            {selectedSensor.range?.minimum?.origin || 'USER_DEFINED'}
                          </span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Zona cega / alcance mínimo
                        </td>
                      </tr>

                      {/* Accuracy Range */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">accuracy.range</td>
                        <td className="p-3 font-mono font-bold text-white">
                          ±{selectedSensor.accuracy?.range?.value ?? '0.02'} {selectedSensor.accuracy?.range?.unit || 'm'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-emerald text-[10px]">1-sigma</span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Incerteza métrica de medição de distância
                        </td>
                      </tr>

                      {/* Horizontal Beam Divergence */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">beam.horizontal_divergence</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.beam?.horizontal_divergence?.value != null
                            ? `${selectedSensor.beam.horizontal_divergence.value} rad (${(selectedSensor.beam.horizontal_divergence.value * 1000).toFixed(2)} mrad)`
                            : '0.0016 rad'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-emerald text-[10px]">
                            {selectedSensor.beam?.beam_shape || 'circular'}
                          </span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Alargamento do feixe laser com a distância
                        </td>
                      </tr>

                      {/* Vertical Beam Divergence */}
                      {selectedSensor.beam?.vertical_divergence?.value != null && (
                        <tr>
                          <td className="p-3 font-mono text-cyan-300 font-semibold">beam.vertical_divergence</td>
                          <td className="p-3 font-mono font-bold text-white">
                            {selectedSensor.beam.vertical_divergence.value} rad ({(selectedSensor.beam.vertical_divergence.value * 1000).toFixed(2)} mrad)
                          </td>
                          <td className="p-3">
                            <span className="badge badge-cyan text-[10px]">known</span>
                          </td>
                          <td className="p-3 text-[11px] text-slate-400">
                            Divergência vertical (feixe elíptico)
                          </td>
                        </tr>
                      )}

                      {/* Wavelength */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">wavelength</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.wavelength?.value ?? '905'} {selectedSensor.wavelength?.unit || 'nm'}
                        </td>
                        <td className="p-3">
                          <span className="badge badge-cyan text-[10px]">óptica</span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Comprimento de onda do laser para cálculo de atenuação atmosférica
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
                          Taxa de repetição de pulsos / pontos por segundo
                        </td>
                      </tr>

                      {/* Rotation Frequency */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">scan.rotation_frequency</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.scan?.rotation_frequency?.value ?? '10'} {selectedSensor.scan?.rotation_frequency?.unit || 'Hz'}{' '}
                          <span className="text-slate-400 font-normal">
                            ({((selectedSensor.scan?.rotation_frequency?.value ?? 10) * 60).toFixed(0)} RPM)
                          </span>
                        </td>
                        <td className="p-3">
                          <span className="badge badge-emerald text-[10px]">known</span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Velocidade de rotação do mecanismo de varredura
                        </td>
                      </tr>

                      {/* Channel Count / FOV */}
                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">angular.channel_count</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.angular?.channel_count?.value ?? selectedSensor.scan?.channels ?? '1'} canais
                        </td>
                        <td className="p-3">
                          <span className="badge badge-cyan text-[10px]">geometria</span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Número de feixes laser simultâneos
                        </td>
                      </tr>

                      <tr>
                        <td className="p-3 font-mono text-cyan-300 font-semibold">angular.fov (H × V)</td>
                        <td className="p-3 font-mono font-bold text-white">
                          {selectedSensor.angular?.horizontal_fov?.value ?? '360'}° × {selectedSensor.angular?.vertical_fov?.value ?? '45'}°
                        </td>
                        <td className="p-3">
                          <span className="badge badge-cyan text-[10px]">campo</span>
                        </td>
                        <td className="p-3 text-[11px] text-slate-400">
                          Campo de visão angular horizontal e vertical
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-16 text-slate-500 text-sm">
              Nenhum sensor selecionado. Escolha um no painel ao lado ou cadastre um novo.
            </div>
          )}
        </div>
      </div>

      {/* Comprehensive Sensor Form Modal (Create / Edit) */}
      {isFormOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="glass-panel p-6 max-w-3xl w-full my-8 space-y-5 border border-white/20 shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                  {formMode === 'create' ? <Plus className="w-5 h-5" /> : <Edit3 className="w-5 h-5" />}
                </div>
                <div>
                  <h4 className="text-lg font-bold text-white">
                    {formMode === 'create' ? 'Cadastrar Novo Sensor LiDAR' : `Editar Sensor: ${selectedSensor?.model}`}
                  </h4>
                  <p className="text-xs text-slate-400">
                    {formMode === 'create'
                      ? 'Preencha as especificações técnicas para registrar o sensor no catálogo de simulação.'
                      : `Modificar parâmetros gerará a nova versão v${selectedSensor?.version} → Bump preservando o histórico imutável (Regra 9).`}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsFormOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error Banner */}
            {formError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            {/* Form Tabs */}
            <div className="flex border-b border-white/10 gap-2 overflow-x-auto pb-1">
              <button
                type="button"
                onClick={() => setFormActiveTab('identity')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  formActiveTab === 'identity'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <Cpu className="w-3.5 h-3.5" /> Identificação
              </button>
              <button
                type="button"
                onClick={() => setFormActiveTab('range')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  formActiveTab === 'range'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <Compass className="w-3.5 h-3.5" /> Alcance & Acurácia
              </button>
              <button
                type="button"
                onClick={() => setFormActiveTab('optics')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  formActiveTab === 'optics'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <Zap className="w-3.5 h-3.5" /> Óptica & Feixe
              </button>
              <button
                type="button"
                onClick={() => setFormActiveTab('scan')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  formActiveTab === 'scan'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <Sliders className="w-3.5 h-3.5" /> Varredura & Canais
              </button>
            </div>

            <form onSubmit={handleSubmitForm} className="space-y-4">
              {/* Tab 1: Identification */}
              {formActiveTab === 'identity' && (
                <div className="space-y-4 animate-in fade-in duration-150">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="form-label">
                        Identificador Único (sensor_id) <span className="text-cyan-400">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        disabled={formMode === 'edit'}
                        value={formData.sensor_id}
                        onChange={(e) => setFormData({ ...formData, sensor_id: e.target.value })}
                        placeholder="ex: riegl-minivux-3uav ou hesai-qt64"
                        className={`form-input font-mono text-xs ${formMode === 'edit' ? 'opacity-60 bg-slate-950 cursor-not-allowed' : ''}`}
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Slug em letras minúsculas, números, hífens ou sublinhados.
                      </p>
                    </div>

                    <div>
                      <label className="form-label">
                        Fabricante (Manufacturer) <span className="text-cyan-400">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.manufacturer}
                        onChange={(e) => setFormData({ ...formData, manufacturer: e.target.value })}
                        placeholder="ex: RIEGL, Ouster, Hesai, Velodyne"
                        className="form-input text-xs"
                      />
                    </div>

                    <div>
                      <label className="form-label">
                        Modelo do Sensor <span className="text-cyan-400">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.model}
                        onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                        placeholder="ex: miniVUX-3UAV, OS1-128"
                        className="form-input text-xs"
                      />
                    </div>

                    <div>
                      <label className="form-label">
                        Arquitetura do Sensor (Sensor Type) <span className="text-cyan-400">*</span>
                      </label>
                      <select
                        value={formData.sensor_type}
                        onChange={(e) => setFormData({ ...formData, sensor_type: e.target.value })}
                        className="form-input text-xs"
                      >
                        <option value="mechanical_spinning">Mechanical Spinning (Varredura Rotativa)</option>
                        <option value="structured_raster">Structured Raster (Varredura Raster)</option>
                        <option value="non_repetitive">Non-Repetitive (Varredura Não-Repetitiva)</option>
                        <option value="other">Outro (Other)</option>
                      </select>
                    </div>

                    <div>
                      <label className="form-label">Versão Inicial / Atual</label>
                      <input
                        type="text"
                        disabled={formMode === 'edit'}
                        value={formData.version}
                        onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                        placeholder="1.0.0"
                        className={`form-input font-mono text-xs ${formMode === 'edit' ? 'opacity-60 bg-slate-950 cursor-not-allowed' : ''}`}
                      />
                      {formMode === 'edit' && (
                        <p className="text-[10px] text-cyan-400 mt-1">
                          A versão é automaticamente incrementada no salvamento.
                        </p>
                      )}
                    </div>

                    <div>
                      <label className="form-label">Status de Validação</label>
                      <select
                        value={formData.validation_status}
                        onChange={(e) => setFormData({ ...formData, validation_status: e.target.value as any })}
                        className="form-input text-xs"
                      >
                        <option value="validated">Validado (Validated)</option>
                        <option value="provisional">Provisório (Provisional)</option>
                        <option value="unvalidated">Não Validado (Unvalidated)</option>
                      </select>
                    </div>

                    <div>
                      <label className="form-label">Revisão de Hardware (Opcional)</label>
                      <input
                        type="text"
                        value={formData.hardware_revision}
                        onChange={(e) => setFormData({ ...formData, hardware_revision: e.target.value })}
                        placeholder="ex: Rev D, Rev 8.0"
                        className="form-input text-xs font-mono"
                      />
                    </div>

                    <div>
                      <label className="form-label">Versão de Firmware (Opcional)</label>
                      <input
                        type="text"
                        value={formData.firmware_version}
                        onChange={(e) => setFormData({ ...formData, firmware_version: e.target.value })}
                        placeholder="ex: v2.4.1"
                        className="form-input text-xs font-mono"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Range & Accuracy */}
              {formActiveTab === 'range' && (
                <div className="space-y-4 animate-in fade-in duration-150">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="form-label">
                        Alcance Máximo (m) <span className="text-cyan-400">*</span>
                      </label>
                      <input
                        type="number"
                        step="any"
                        required
                        value={formData.range_max}
                        onChange={(e) => setFormData({ ...formData, range_max: e.target.value })}
                        placeholder="ex: 250"
                        className="form-input font-mono text-xs"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Distância máxima operacional do sensor (usada no cálculo de detecção).
                      </p>
                    </div>

                    <div>
                      <label className="form-label">Alcance Mínimo (m)</label>
                      <input
                        type="number"
                        step="any"
                        value={formData.range_min}
                        onChange={(e) => setFormData({ ...formData, range_min: e.target.value })}
                        placeholder="ex: 1.0"
                        className="form-input font-mono text-xs"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Zona cega ou menor distância mensurável pelo sensor.
                      </p>
                    </div>

                    <div>
                      <label className="form-label">Acurácia de Alcance (m)</label>
                      <input
                        type="number"
                        step="any"
                        value={formData.accuracy_range}
                        onChange={(e) => setFormData({ ...formData, accuracy_range: e.target.value })}
                        placeholder="ex: 0.015 (15 mm)"
                        className="form-input font-mono text-xs"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Incerteza sistemática de medição de distância (1-sigma).
                      </p>
                    </div>

                    <div>
                      <label className="form-label">Precisão / Repetibilidade (m)</label>
                      <input
                        type="number"
                        step="any"
                        value={formData.precision_range}
                        onChange={(e) => setFormData({ ...formData, precision_range: e.target.value })}
                        placeholder="ex: 0.010 (10 mm)"
                        className="form-input font-mono text-xs"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Ruído aleatório de medição em superfície plana.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Optics & Beam */}
              {formActiveTab === 'optics' && (
                <div className="space-y-4 animate-in fade-in duration-150">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="form-label">
                        Divergência Horizontal do Feixe (mrad) <span className="text-cyan-400">*</span>
                      </label>
                      <input
                        type="number"
                        step="any"
                        required
                        value={formData.beam_h_div_mrad}
                        onChange={(e) => setFormData({ ...formData, beam_h_div_mrad: e.target.value })}
                        placeholder="ex: 1.6 (mrad)"
                        className="form-input font-mono text-xs"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Em milirradianos. Convertido automaticamente para radianos para a simulação física.
                      </p>
                    </div>

                    <div>
                      <label className="form-label">Divergência Vertical do Feixe (mrad)</label>
                      <input
                        type="number"
                        step="any"
                        value={formData.beam_v_div_mrad}
                        onChange={(e) => setFormData({ ...formData, beam_v_div_mrad: e.target.value })}
                        placeholder="ex: 0.5 (mrad)"
                        className="form-input font-mono text-xs"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Para feixes elípticos; caso seja circular, deixe igual à horizontal.
                      </p>
                    </div>

                    <div>
                      <label className="form-label">Geometria do Feixe (Beam Shape)</label>
                      <select
                        value={formData.beam_shape}
                        onChange={(e) => setFormData({ ...formData, beam_shape: e.target.value as any })}
                        className="form-input text-xs"
                      >
                        <option value="elliptical">Elíptico (Elliptical)</option>
                        <option value="circular">Circular</option>
                        <option value="gaussian">Gaussiano (Gaussian)</option>
                        <option value="unknown">Desconhecido (Unknown)</option>
                      </select>
                    </div>

                    <div>
                      <label className="form-label">Comprimento de Onda do Laser (nm)</label>
                      <input
                        type="number"
                        step="any"
                        value={formData.wavelength}
                        onChange={(e) => setFormData({ ...formData, wavelength: e.target.value })}
                        placeholder="ex: 905 ou 1550"
                        className="form-input font-mono text-xs"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Wavelength em nanômetros (ex: 905 nm, 865 nm, 1550 nm).
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 4: Scan Dynamics */}
              {formActiveTab === 'scan' && (
                <div className="space-y-4 animate-in fade-in duration-150">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="form-label">
                        Taxa de Pontos (point_rate) [pts/s ou Hz] <span className="text-cyan-400">*</span>
                      </label>
                      <input
                        type="number"
                        step="any"
                        required
                        value={formData.point_rate}
                        onChange={(e) => setFormData({ ...formData, point_rate: e.target.value })}
                        placeholder="ex: 600000 ou 1310720"
                        className="form-input font-mono text-xs"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Capacidade de medição de pulsos por segundo do sensor.
                      </p>
                    </div>

                    <div>
                      <label className="form-label">
                        Frequência de Rotação (Hz) <span className="text-cyan-400">*</span>
                      </label>
                      <input
                        type="number"
                        step="any"
                        required
                        value={formData.rotation_freq}
                        onChange={(e) => setFormData({ ...formData, rotation_freq: e.target.value })}
                        placeholder="ex: 10 ou 20 (Hz)"
                        className="form-input font-mono text-xs"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        10 Hz = 600 RPM; 20 Hz = 1200 RPM.
                      </p>
                    </div>

                    <div>
                      <label className="form-label">Taxa de Quadros / Frame Rate (Hz)</label>
                      <input
                        type="number"
                        step="any"
                        value={formData.frame_rate}
                        onChange={(e) => setFormData({ ...formData, frame_rate: e.target.value })}
                        placeholder="ex: 10 ou 20"
                        className="form-input font-mono text-xs"
                      />
                    </div>

                    <div>
                      <label className="form-label">Número de Canais / Linhas Laser</label>
                      <input
                        type="number"
                        step="1"
                        min="1"
                        value={formData.channel_count}
                        onChange={(e) => setFormData({ ...formData, channel_count: e.target.value })}
                        placeholder="ex: 1 (miniVUX), 32, 64, 128 (Ouster/Hesai)"
                        className="form-input font-mono text-xs"
                      />
                    </div>

                    <div>
                      <label className="form-label">Campo de Visão Horizontal (graus)</label>
                      <input
                        type="number"
                        step="any"
                        value={formData.fov_horizontal}
                        onChange={(e) => setFormData({ ...formData, fov_horizontal: e.target.value })}
                        placeholder="ex: 360"
                        className="form-input font-mono text-xs"
                      />
                    </div>

                    <div>
                      <label className="form-label">Campo de Visão Vertical (graus)</label>
                      <input
                        type="number"
                        step="any"
                        value={formData.fov_vertical}
                        onChange={(e) => setFormData({ ...formData, fov_vertical: e.target.value })}
                        placeholder="ex: 45 ou 90"
                        className="form-input font-mono text-xs"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Navigation & Submit Buttons */}
              <div className="flex items-center justify-between pt-4 border-t border-white/10">
                <div className="flex items-center gap-2">
                  {formActiveTab !== 'identity' && (
                    <button
                      type="button"
                      onClick={() => {
                        if (formActiveTab === 'scan') setFormActiveTab('optics');
                        else if (formActiveTab === 'optics') setFormActiveTab('range');
                        else if (formActiveTab === 'range') setFormActiveTab('identity');
                      }}
                      className="btn-secondary text-xs"
                    >
                      ← Aba Anterior
                    </button>
                  )}
                  {formActiveTab !== 'scan' && (
                    <button
                      type="button"
                      onClick={() => {
                        if (formActiveTab === 'identity') setFormActiveTab('range');
                        else if (formActiveTab === 'range') setFormActiveTab('optics');
                        else if (formActiveTab === 'optics') setFormActiveTab('scan');
                      }}
                      className="btn-secondary text-xs"
                    >
                      Próxima Aba →
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setIsFormOpen(false)}
                    className="btn-secondary text-xs"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="btn-primary text-xs flex items-center gap-1.5 shadow-lg shadow-cyan-950/40"
                  >
                    <CheckCircle className="w-4 h-4 text-cyan-300" />
                    {isSubmitting
                      ? 'Salvando...'
                      : formMode === 'create'
                      ? 'Cadastrar Sensor'
                      : 'Salvar Alterações & Versionar'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && selectedSensor && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="glass-panel p-6 max-w-md w-full space-y-4 border border-rose-500/30 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-white">Excluir Sensor</h4>
                <p className="text-xs text-rose-300">Confirmação de exclusão permanente</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Você tem certeza de que deseja remover o sensor{' '}
              <strong className="text-white font-mono">{selectedSensor.model}</strong> (
              <span className="font-mono text-cyan-400">{selectedSensor.sensor_id}</span>)? Esta ação removerá o
              sensor do catálogo de simulações.
            </p>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/10">
              <button
                type="button"
                onClick={() => setIsDeleteModalOpen(false)}
                disabled={isDeleting}
                className="btn-secondary text-xs"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleDeleteSensor}
                disabled={isDeleting}
                className="p-2 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs transition-all flex items-center gap-1.5 shadow-lg shadow-rose-950/50"
              >
                <Trash2 className="w-4 h-4" />
                {isDeleting ? 'Excluindo...' : 'Confirmar Exclusão'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
