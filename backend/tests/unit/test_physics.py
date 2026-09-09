"""Physics engine tests (PRD sections 25-34).

Tests:
  - Beam/target overlap
  - Return strength model
  - Detection probability (datasheet, analytical, assumption, insufficient_data)
  - Measurement model (bias + noise)
  - Error definition conversion
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from lidar_analysis.physics.beam import (
    beam_target_overlap,
    return_strength,
    effective_illuminated_area_cylinder,
)
from lidar_analysis.physics.detection import (
    AnalyticalModel,
    AssumptionModel,
    DatasheetModel,
    DetectionModelType,
    insufficient_data_result,
)
from lidar_analysis.physics.measurement import (
    MeasurementConfig,
    MeasurementModel,
    convert_sigma,
)
from lidar_analysis.models.common import ErrorDefinition, ConfidenceLevel


class TestBeamOverlap:
    def test_full_overlap(self):
        """Target larger than beam → G = 1.0."""
        assert beam_target_overlap(0.5, 0.1) == 1.0

    def test_partial_overlap(self):
        """Beam larger than target → G < 1.0."""
        g = beam_target_overlap(0.05, 0.1)
        assert np.isclose(g, 0.5)

    def test_no_overlap(self):
        assert beam_target_overlap(0.0, 0.1) == 0.0

    def test_zero_beam(self):
        assert beam_target_overlap(0.1, 0.0) == 0.0


class TestReturnStrength:
    def test_basic(self):
        """S ∝ ρ * A_eff * cos(α) / R²."""
        s = return_strength(reflectivity=0.5, effective_area=0.01, incidence_angle=0, range_to_target=10)
        expected = 0.5 * 0.01 * 1.0 / 100
        assert np.isclose(s, expected)

    def test_grazing_incidence(self):
        """At 90° incidence, cos(α) = 0 → S = 0."""
        s = return_strength(0.5, 0.01, math.pi / 2, 10)
        assert np.isclose(s, 0.0)

    def test_zero_range(self):
        assert return_strength(0.5, 0.01, 0, 0) == 0.0


class TestEffectiveArea:
    def test_cylinder_area(self):
        area = effective_illuminated_area_cylinder(
            beam_diameter=0.1,
            target_diameter=0.05,
            incidence_angle=0.0,
        )
        assert area > 0

    def test_grazing_area(self):
        area = effective_illuminated_area_cylinder(0.1, 0.05, math.pi / 2)
        assert np.isclose(area, 0.0)


class TestDetectionModels:
    def test_datasheet_within_range(self):
        m = DatasheetModel(max_range=50, min_reflectivity=0.1)
        r = m.compute_detection_probability(30, 0.3, 0, 1.0, 1e-3)
        assert r.probability == 1.0
        assert r.model_type == DetectionModelType.DATASHEET

    def test_datasheet_beyond_range(self):
        m = DatasheetModel(max_range=50)
        r = m.compute_detection_probability(60, 0.3, 0, 1.0, 1e-3)
        assert r.probability == 0.0

    def test_datasheet_low_reflectivity(self):
        m = DatasheetModel(max_range=50, min_reflectivity=0.5)
        r = m.compute_detection_probability(30, 0.3, 0, 1.0, 1e-3)
        assert r.probability == 0.0

    def test_analytical_high_strength(self):
        m = AnalyticalModel(strength_threshold=1e-4, sigmoid_steepness=5000)
        r = m.compute_detection_probability(10, 0.5, 0, 1.0, 1e-3)
        assert r.probability is not None
        assert r.probability > 0.9

    def test_analytical_low_strength(self):
        m = AnalyticalModel(strength_threshold=1e-4, sigmoid_steepness=5000)
        r = m.compute_detection_probability(100, 0.1, 0, 0.1, 1e-8)
        assert r.probability is not None
        assert r.probability < 0.1

    def test_analytical_beyond_max_range(self):
        m = AnalyticalModel(max_range=50)
        r = m.compute_detection_probability(60, 0.5, 0, 1.0, 1e-3)
        assert r.probability == 0.0

    def test_assumption_fixed(self):
        m = AssumptionModel(assumed_probability=0.5)
        r = m.compute_detection_probability(10, 0.3, 0, 1.0, 1e-3)
        assert r.probability == 0.5

    def test_assumption_insufficient_data(self):
        m = AssumptionModel(assumed_probability=None)
        r = m.compute_detection_probability(10, 0.3, 0, 1.0, 1e-3)
        assert r.probability is None
        assert r.physical_model_confidence == ConfidenceLevel.INSUFFICIENT

    def test_insufficient_data_helper(self):
        r = insufficient_data_result()
        assert r.probability is None
        assert r.notes is not None and "Not reliably" in r.notes


class TestMeasurementModel:
    def test_noisy_measurement(self):
        cfg = MeasurementConfig(bias=0.0, sigma=0.02, error_definition=ErrorDefinition.ONE_SIGMA)
        model = MeasurementModel(range_config=cfg, angular_config=cfg)
        rng = np.random.default_rng(42)
        sample = model.apply(30.0, 0.0, 0.0, rng)
        # should be close to true range but not exact
        assert abs(sample.measured_range - 30.0) < 0.2
        assert sample.true_range == 30.0

    def test_bias(self):
        cfg = MeasurementConfig(bias=0.05, sigma=0.0)
        model = MeasurementModel(range_config=cfg, angular_config=cfg)
        rng = np.random.default_rng(42)
        sample = model.apply(30.0, 0.0, 0.0, rng)
        assert np.isclose(sample.measured_range, 30.05)

    def test_deterministic_with_seed(self):
        cfg = MeasurementConfig(bias=0.0, sigma=0.02)
        model = MeasurementModel(range_config=cfg, angular_config=cfg)
        rng1 = np.random.default_rng(123)
        rng2 = np.random.default_rng(123)
        s1 = model.apply(30.0, 0.1, 0.05, rng1)
        s2 = model.apply(30.0, 0.1, 0.05, rng2)
        assert np.isclose(s1.measured_range, s2.measured_range)

    def test_error_distribution(self):
        """With many samples, std should approximate sigma."""
        sigma = 0.02
        cfg = MeasurementConfig(bias=0.0, sigma=sigma)
        model = MeasurementModel(range_config=cfg, angular_config=cfg)
        rng = np.random.default_rng(42)
        samples = [model.apply(30.0, 0.0, 0.0, rng).measured_range - 30.0 for _ in range(10000)]
        assert abs(np.std(samples) - sigma) < 0.003


class TestErrorConversion:
    def test_identity(self):
        assert np.isclose(convert_sigma(0.02, ErrorDefinition.ONE_SIGMA, ErrorDefinition.ONE_SIGMA), 0.02)

    def test_1sigma_to_2sigma(self):
        assert np.isclose(convert_sigma(0.02, ErrorDefinition.ONE_SIGMA, ErrorDefinition.TWO_SIGMA), 0.04)

    def test_1sigma_to_95(self):
        assert np.isclose(convert_sigma(0.02, ErrorDefinition.ONE_SIGMA, ErrorDefinition.PERCENT_95), 0.02 * 1.96)

    def test_2sigma_to_1sigma(self):
        assert np.isclose(convert_sigma(0.04, ErrorDefinition.TWO_SIGMA, ErrorDefinition.ONE_SIGMA), 0.02)

    def test_95_to_1sigma(self):
        assert np.isclose(convert_sigma(0.0392, ErrorDefinition.PERCENT_95, ErrorDefinition.ONE_SIGMA), 0.02)