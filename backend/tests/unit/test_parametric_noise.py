"""Unit tests for the Parametric Range Noise Model (Generalized Exponential)
and multi-return support in SingleTrialEngine.
"""

import math
import numpy as np
import pytest
from pathlib import Path

from lidar_analysis.models.sensor import Sensor
from lidar_analysis.physics.measurement import (
    compute_parametric_range_noise,
    MeasurementConfig,
    MeasurementModel,
)
from lidar_analysis.simulation.engine import SingleTrialEngine


class TestParametricRangeNoise:
    def test_noise_at_boundaries(self):
        sigma_min = 0.005  # 5 mm
        sigma_max = 0.030  # 30 mm
        d_max = 100.0  # 100 m

        # At d = 0, must equal sigma_min
        assert compute_parametric_range_noise(0.0, sigma_min, sigma_max, d_max) == pytest.approx(sigma_min)

        # At d = d_max, must equal sigma_max
        assert compute_parametric_range_noise(100.0, sigma_min, sigma_max, d_max) == pytest.approx(sigma_max)

    def test_noise_at_intermediate_distance(self):
        sigma_min = 0.01
        sigma_max = 0.04
        d_max = 100.0

        # At d = 50 m (halfway): sigma = 0.01 * (0.04 / 0.01)**(0.5) = 0.01 * 2 = 0.02
        expected_half = sigma_min * math.sqrt(sigma_max / sigma_min)
        assert compute_parametric_range_noise(50.0, sigma_min, sigma_max, d_max) == pytest.approx(expected_half)

    def test_out_of_bounds_clamping(self):
        sigma_min = 0.005
        sigma_max = 0.025
        d_max = 60.0

        # d < 0 returns sigma_min
        assert compute_parametric_range_noise(-10.0, sigma_min, sigma_max, d_max) == pytest.approx(sigma_min)

        # d > d_max returns sigma_max
        assert compute_parametric_range_noise(120.0, sigma_min, sigma_max, d_max) == pytest.approx(sigma_max)

    def test_invalid_parameters_safe_guards(self):
        # sigma_min <= 0 is safely guarded to positive floor
        val_zero_min = compute_parametric_range_noise(10.0, 0.0, 0.03, 100.0)
        assert val_zero_min > 0
        assert not math.isnan(val_zero_min)

        # sigma_max < sigma_min is guarded so sigma_max >= sigma_min
        val_inverted = compute_parametric_range_noise(10.0, 0.05, 0.02, 100.0)
        assert val_inverted >= 0.05

        # d_max <= 0 safely returns sigma_min
        assert compute_parametric_range_noise(10.0, 0.01, 0.03, 0.0) == pytest.approx(0.01)


class TestMeasurementConfigWithNoiseModel:
    def test_measurement_config_get_sigma_parametric(self):
        cfg = MeasurementConfig(
            sigma=0.02,
            sigma_min=0.005,
            sigma_max=0.030,
            d_max=100.0,
        )
        assert cfg.get_sigma(0.0) == pytest.approx(0.005)
        assert cfg.get_sigma(100.0) == pytest.approx(0.030)
        assert cfg.get_sigma(50.0) == pytest.approx(0.005 * math.sqrt(6.0))

    def test_measurement_config_get_sigma_fallback(self):
        cfg = MeasurementConfig(
            sigma=0.02,
        )
        # Without parametric parameters, returns static sigma
        assert cfg.get_sigma(0.0) == pytest.approx(0.02)
        assert cfg.get_sigma(100.0) == pytest.approx(0.02)


class TestMultiReturnResolution:
    def test_returns_per_pulse_impact(self):
        from lidar_analysis.geometry.targets import Cylinder
        from lidar_analysis.physics.detection import DatasheetModel

        target = Cylinder.from_dbh(0.20, [20, 0, 0], [0, 0, 1], 0.3)
        det_model = DatasheetModel(max_range=100)
        range_cfg = MeasurementConfig(sigma=0.01)
        ang_cfg = MeasurementConfig(sigma=0.001)
        model = MeasurementModel(range_config=range_cfg, angular_config=ang_cfg)
        rng = np.random.default_rng(42)

        engine_single = SingleTrialEngine(
            target=target,
            detection_model=det_model,
            measurement_model=model,
            beam_divergence=0.002,
            rng=rng,
            returns_per_pulse=1,
        )
        engine_multi = SingleTrialEngine(
            target=target,
            detection_model=det_model,
            measurement_model=model,
            beam_divergence=0.002,
            rng=rng,
            returns_per_pulse=3,
        )

        assert engine_single.returns_per_pulse == 1
        assert engine_multi.returns_per_pulse == 3


class TestCanonicalSensorsLoadValid:
    def test_all_sensors_load_with_new_fields(self):
        sensors_dir = Path(__file__).resolve().parents[3] / "data" / "sensors"
        assert sensors_dir.exists(), f"Sensors dir {sensors_dir} does not exist"

        for json_file in sensors_dir.glob("*.json"):
            sensor = Sensor.model_validate_json(json_file.read_text(encoding="utf-8"))
            assert sensor.sensor_id is not None
            # Check maximum range is defined
            if sensor.range and sensor.range.maximum:
                assert sensor.range.maximum.value is not None
            # Check scan returns_per_pulse defaults or matches
            if sensor.scan:
                assert sensor.scan.returns_per_pulse >= 1
