import type { Scenario, Sensor, SimulationJob, SimulationRequest, StandardError } from './types';

const BASE_URL = '';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const resp = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!resp.ok) {
    let errorData: StandardError;
    try {
      errorData = await resp.json();
    } catch {
      errorData = {
        error: {
          code: 'HTTP_ERROR',
          message: `Request failed with status ${resp.status}: ${resp.statusText}`,
        },
      };
    }
    const message = errorData.error?.message || errorData.detail || `Request failed (${resp.status})`;
    throw new Error(message);
  }

  return resp.json();
}

export const api = {
  // Health
  checkHealth: () => request<{ status: string }>('/health'),

  // Sensors
  listSensors: () => request<Sensor[]>('/api/sensors'),
  getSensor: (id: string) => request<Sensor>(`/api/sensors/${id}`),
  createSensor: (sensor: Sensor) =>
    request<{ sensor_id: string; status: string }>('/api/sensors', {
      method: 'POST',
      body: JSON.stringify(sensor),
    }),
  updateSensor: (id: string, sensor: Sensor) =>
    request<{ sensor_id: string; status: string; version: string }>(`/api/sensors/${id}`, {
      method: 'PUT',
      body: JSON.stringify(sensor),
    }),
  deleteSensor: (id: string) =>
    request<{ sensor_id: string; status: string }>(`/api/sensors/${id}`, {
      method: 'DELETE',
    }),
  listSensorVersions: (id: string) =>
    request<Array<{ version: string; sensor: Sensor }>>(`/api/sensors/${id}/versions`),

  // Scenarios
  listScenarios: () => request<Scenario[]>('/api/scenarios'),
  getScenario: (id: string) => request<Scenario>(`/api/scenarios/${id}`),
  createScenario: (scenario: Scenario) =>
    request<{ scenario_id: string; status: string }>('/api/scenarios', {
      method: 'POST',
      body: JSON.stringify(scenario),
    }),
  updateScenario: (id: string, scenario: Scenario) =>
    request<{ scenario_id: string; status: string }>(`/api/scenarios/${id}`, {
      method: 'PUT',
      body: JSON.stringify(scenario),
    }),

  // Simulations
  createSimulation: (simReq: SimulationRequest) =>
    request<{ simulation_id: string; status: string }>('/api/simulations', {
      method: 'POST',
      body: JSON.stringify(simReq),
    }),
  getSimulation: (id: string) => request<SimulationJob>(`/api/simulations/${id}`),
  getSimulationResults: (id: string) => request<any>(`/api/simulations/${id}/results`),
  cancelSimulation: (id: string) =>
    request<{ simulation_id: string; status: string }>(`/api/simulations/${id}/cancel`, {
      method: 'POST',
    }),

  // Analysis sweeps
  runDistanceSweep: (body: any) =>
    request<any>('/api/analysis/distance-sweep', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  runDbhSweep: (body: any) =>
    request<any>('/api/analysis/dbh-sweep', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  compareSensors: (body: any) =>
    request<any>('/api/analysis/compare', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // Reports
  createReport: (simulationId: string, format = 'markdown') =>
    request<{ report_id: string; status: string; format: string }>('/api/reports', {
      method: 'POST',
      body: JSON.stringify({ simulation_id: simulationId, format }),
    }),
  getReport: (reportId: string) =>
    request<{ report_id: string; status: string; format: string; body: string }>(
      `/api/reports/${reportId}`
    ),

  // Datasheets
  extractDatasheet: async (
    file: File,
    useLlm: boolean = false,
    llmModel: string = 'z-ai/glm-5.3-flash'
  ) => {
    let text = '';
    try {
      text = await file.text();
    } catch {
      text = '';
    }
    const payload = {
      filename: file.name,
      content_type: file.type || 'text/plain',
      data: { text },
      use_llm: useLlm,
      llm_model: llmModel,
    };
    return request<any>('/api/datasheets/extract', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  validateDatasheet: (extractionId: string, validatedParameters: Record<string, any>) =>
    request<any>(`/api/datasheets/${extractionId}/validate`, {
      method: 'POST',
      body: JSON.stringify({ validated_parameters: validatedParameters }),
    }),
};
