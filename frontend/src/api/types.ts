export interface ParameterValue<T = number> {
  value: T | null;
  unit: string;
  origin: 'MANUFACTURER' | 'CALIBRATION' | 'USER_DEFINED' | 'ASSUMED' | 'DERIVED' | 'SOURCE' | 'SYSTEM_DEFAULT';
  status: 'known' | 'estimated' | 'unknown' | 'not_applicable';
  definition?: string;
  conditions?: Record<string, any>;
  provenance?: {
    document?: string;
    page?: number;
    section?: string;
    table?: string;
    extracted_text?: string;
    confidence?: number;
  };
}

export interface Sensor {
  sensor_id: string;
  sensor_type: string;
  manufacturer: string;
  model: string;
  version: string;
  hardware_revision?: string;
  firmware_version?: string;
  description?: string;
  wavelength?: ParameterValue<number>;
  range?: {
    maximum?: ParameterValue<number>;
    minimum?: ParameterValue<number>;
    reflectivity_curves?: any[];
  };
  accuracy?: {
    range?: ParameterValue<number>;
    angular?: ParameterValue<number>;
    angular_horizontal?: ParameterValue<number>;
    angular_vertical?: ParameterValue<number>;
    definition?: string;
  };
  precision?: {
    range?: ParameterValue<number>;
    angular?: ParameterValue<number>;
    angular_horizontal?: ParameterValue<number>;
    angular_vertical?: ParameterValue<number>;
    definition?: string;
  };
  angular?: {
    horizontal_fov?: ParameterValue<number>;
    vertical_fov?: ParameterValue<number>;
    horizontal_resolution?: ParameterValue<number>;
    vertical_resolution?: ParameterValue<number>;
    channel_count?: ParameterValue<number>;
  };
  beam?: {
    beam_shape?: 'circular' | 'elliptical' | 'gaussian' | 'unknown';
    shape?: string;
    horizontal_divergence?: ParameterValue<number>;
    vertical_divergence?: ParameterValue<number>;
  };
  scan?: {
    type?: string;
    point_rate?: ParameterValue<number>;
    rotation_frequency?: ParameterValue<number>;
    frame_rate?: ParameterValue<number>;
    channels?: number;
  };
  validation?: {
    status: 'unvalidated' | 'provisional' | 'validated' | 'deprecated';
    validated_by?: string;
    validated_at?: string;
  };
  provenance?: any[];
  assumptions?: any[];
}

export interface TargetConfig {
  type: 'cylinder' | 'box';
  diameter?: number; // DBH for cylinder
  height?: number;
  width?: number;
  depth?: number;
  position: [number, number, number];
  orientation: [number, number, number];
  reflectivity: number;
}

export interface Scenario {
  scenario_id: string;
  sensor_id: string;
  environment: {
    atmosphere?: 'clear' | 'rain' | 'fog' | 'dust';
    rain_rate_mm_hr?: number;
    fog_visibility_m?: number;
    dust_concentration_mg_m3?: number;
    vegetation?: 'none' | 'sparse' | 'moderate' | 'dense';
  };
  sensor_pose: {
    position: [number, number, number];
    orientation: {
      yaw: number;
      pitch: number;
      roll: number;
    };
  };
  target: TargetConfig;
}

export interface SimulationRequest {
  scenario_id: string;
  mode: 'monte_carlo' | 'analytical' | 'synthetic_point_cloud';
  duration: number;
  monte_carlo?: {
    enabled?: boolean;
    trials?: number;
    random_seed?: number;
  };
  detection_model_id?: string;
  measurement_model?: {
    range_bias?: number;
    range_sigma?: number;
    range_error_definition?: string;
    angular_bias?: number;
    angular_sigma?: number;
    angular_error_definition?: string;
  };
}

export interface SimulationJob {
  simulation_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  trials_completed: number;
  trials_total: number;
  result?: any;
  error?: string;
}

export interface StandardError {
  error: {
    code: string;
    message: string;
    field?: string | null;
    details?: Record<string, any>;
  };
  detail?: any;
}
