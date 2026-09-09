"""Simulation engine + Monte Carlo tests (PRD sections 35-44).

Tests:
  - Single trial: hit/miss, detection, measurement
  - Monte Carlo: statistics, classification, determinism
  - Distance sweep: effective ranges
  - PRD §64 Level 2: ideal target → known returns; P_d=0 → zero detections; P_d=1 → all detected
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from lidar_analysis.geometry.targets import Cylinder
from lidar_analysis.geometry.rays import direction_from_angles
from lidar_analysis.physics.detection import AnalyticalModel, AssumptionModel, DatasheetModel
from lidar_analysis.physics.measurement import MeasurementConfig, MeasurementModel
from lidar_analysis.models.common import ErrorDefinition
from lidar_analysis.scan.scanners import ScanPoint, MechanicalSpinningScanner, Channel
from lidar_analysis.simulation.engine import SingleTrialEngine
from lidar_analysis.simulation.monte_carlo import MonteCarloEngine
from lidar_analysis.simulation.analysis import (
    classify,
    distance_sweep,
    find_effective_ranges,
)


def _make_scan_point(h_angle: float = 0.0, v_angle: float = 0.0) -> ScanPoint:
    d = direction_from_angles(h_angle, v_angle)
    return ScanPoint(
        horizontal_angle=h_angle,
        vertical_angle=v_angle,
        channel_index=0,
        time=0.0,
        direction=d,
    )


@pytest.fixture()
def cylinder_target():
    return Cylinder.from_dbh(0.10, [30, 0, 0], [0, 0, 1], 0.3)


@pytest.fixture()
def measurement_model():
    cfg = MeasurementConfig(bias=0.0, sigma=0.02, error_definition=ErrorDefinition.ONE_SIGMA)
    return MeasurementModel(range_config=cfg, angular_config=cfg)


class TestSingleTrial:
    def test_hit_detected(self, cylinder_target, measurement_model):
        """Ray aimed at target hits and gets detected with high P_d."""
        engine = SingleTrialEngine(
            target=cylinder_target,
            detection_model=DatasheetModel(max_range=50),
            measurement_model=measurement_model,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        sp = _make_scan_point()
        sensor_pos = np.array([0, 0, 0.0])
        result = engine.run([sp], sensor_pos)
        assert result.hits >= 1
        assert result.detections >= 1

    def test_miss_no_detection(self, cylinder_target, measurement_model):
        """Ray aimed away from target misses entirely."""
        engine = SingleTrialEngine(
            target=cylinder_target,
            detection_model=DatasheetModel(max_range=50),
            measurement_model=measurement_model,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        # aim at 90 degrees — won't hit cylinder at [30,0,0]
        sp = _make_scan_point(h_angle=math.pi / 2)
        sensor_pos = np.array([0, 0, 0.0])
        result = engine.run([sp], sensor_pos)
        assert result.hits == 0
        assert result.detections == 0

    def test_pd_zero_no_detections(self, cylinder_target, measurement_model):
        """PRD §64 Level 2: P_d=0 → zero detections even on hits."""
        engine = SingleTrialEngine(
            target=cylinder_target,
            detection_model=AssumptionModel(assumed_probability=0.0),
            measurement_model=measurement_model,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        sp = _make_scan_point()
        result = engine.run([sp], np.array([0, 0, 0.0]))
        assert result.detections == 0

    def test_pd_one_all_detected(self, cylinder_target, measurement_model):
        """PRD §64 Level 2: P_d=1 → all hits detected."""
        engine = SingleTrialEngine(
            target=cylinder_target,
            detection_model=AssumptionModel(assumed_probability=1.0),
            measurement_model=measurement_model,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        sp = _make_scan_point()
        result = engine.run([sp], np.array([0, 0, 0.0]))
        assert result.hits == result.detections
        assert result.detections >= 1

    def test_measurement_applied(self, cylinder_target, measurement_model):
        """Detected points get measurement error applied."""
        engine = SingleTrialEngine(
            target=cylinder_target,
            detection_model=AssumptionModel(assumed_probability=1.0),
            measurement_model=measurement_model,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        sp = _make_scan_point()
        result = engine.run([sp], np.array([0, 0, 0.0]))
        for rec in result.detected_records:
            assert rec.measurement is not None
            assert rec.measurement.measured_range != rec.measurement.true_range or \
                   measurement_model.range_config.sigma == 0.0


class TestMonteCarlo:
    def test_statistics(self, cylinder_target, measurement_model):
        """MC produces valid statistics."""
        engine = SingleTrialEngine(
            target=cylinder_target,
            detection_model=DatasheetModel(max_range=50),
            measurement_model=measurement_model,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        sp = _make_scan_point()
        mc = MonteCarloEngine(engine, n_trials=100, seed=42)
        result = mc.run([sp], np.array([0, 0, 0.0]))
        assert result.n_trials == 100
        assert result.detection_count_stats.mean >= 0
        assert result.detection_count_stats.std >= 0

    def test_deterministic(self, cylinder_target, measurement_model):
        """Same seed → same results."""
        def _run(seed):
            e = SingleTrialEngine(
                target=cylinder_target,
                detection_model=DatasheetModel(max_range=50),
                measurement_model=measurement_model,
                beam_divergence=0.003,
                rng=np.random.default_rng(seed),
            )
            mc = MonteCarloEngine(e, n_trials=50, seed=seed)
            return mc.run([_make_scan_point()], np.array([0, 0, 0.0]))

        r1 = _run(123)
        r2 = _run(123)
        np.testing.assert_array_equal(r1.detection_counts, r2.detection_counts)

    def test_classification(self, cylinder_target, measurement_model):
        """Classification returns correct structure."""
        engine = SingleTrialEngine(
            target=cylinder_target,
            detection_model=DatasheetModel(max_range=50),
            measurement_model=measurement_model,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        # Multiple scan points to get enough detections
        scanner = MechanicalSpinningScanner(
            horizontal_fov=math.radians(10),
            vertical_fov=math.radians(10),
            channels=[Channel(elevation_angle=0.0)],
            point_rate=100,
            rotation_frequency=10,
        )
        scan_points = scanner.generate_scan_points(duration=0.1)
        mc = MonteCarloEngine(engine, n_trials=10, seed=42)
        result = mc.run(scan_points, np.array([0, 0, 0.0]))
        cls = classify(result)
        assert isinstance(cls.detected, bool)
        assert 0 <= cls.p_detected <= 1

    def test_n_trials_range(self, cylinder_target, measurement_model):
        engine = SingleTrialEngine(
            target=cylinder_target,
            detection_model=DatasheetModel(max_range=50),
            measurement_model=measurement_model,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        with pytest.raises(ValueError, match="n_trials"):
            MonteCarloEngine(engine, n_trials=0)


class TestDistanceSweep:
    def test_sweep_finds_ranges(self, measurement_model):
        """Distance sweep should find decreasing detection at longer ranges."""
        def factory(dist):
            target = Cylinder.from_dbh(0.10, [dist, 0, 0], [0, 0, 1], 0.3)
            return SingleTrialEngine(
                target=target,
                detection_model=DatasheetModel(max_range=50),
                measurement_model=measurement_model,
                beam_divergence=0.003,
                rng=np.random.default_rng(42),
            )

        distances = np.array([10, 20, 30, 40, 60])
        scan_points = [_make_scan_point()]
        sweep = distance_sweep(
            engine_factory=factory,
            distances=distances,
            n_trials=20,
            seed=42,
            scan_points=scan_points,
            sensor_position=np.array([0, 0, 0.0]),
        )
        assert len(sweep.points) == 5
        # At 10m should have high detection, at 60m should have 0
        assert sweep.points[0].p_detected >= sweep.points[-1].p_detected

    def test_effective_ranges(self, measurement_model):
        """Effective ranges should respect ordering R_char ≤ R_rel ≤ R_det."""
        def factory(dist):
            target = Cylinder.from_dbh(0.10, [dist, 0, 0], [0, 0, 1], 0.3)
            return SingleTrialEngine(
                target=target,
                detection_model=DatasheetModel(max_range=50),
                measurement_model=measurement_model,
                beam_divergence=0.003,
                rng=np.random.default_rng(42),
            )

        distances = np.linspace(5, 60, 12)
        sweep = distance_sweep(
            engine_factory=factory,
            distances=distances,
            n_trials=20,
            seed=42,
            scan_points=[_make_scan_point()],
            sensor_position=np.array([0, 0, 0.0]),
        )
        ranges = find_effective_ranges(sweep)
        assert ranges.characterization_range <= ranges.reliable_range or ranges.reliable_range == 0
        assert ranges.reliable_range <= ranges.detection_range or ranges.detection_range == 0