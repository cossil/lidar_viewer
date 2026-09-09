"""End-to-end integration tests.

PRD section 64: Level 2 synthetic validation.
- Ideal target → returns match configured detection model.
- No intersection → zero detections.
- Zero probability → zero detections.
- Full pipeline: sensor → scenario → scan → geometry → physics → simulation → results → report.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from lidar_analysis.geometry.targets import Cylinder, Box
from lidar_analysis.geometry.rays import direction_from_angles
from lidar_analysis.geometry.intersection import ray_cylinder_intersection
from lidar_analysis.geometry.angular_size import target_angular_size, beam_footprint, incidence_angle
from lidar_analysis.physics.beam import beam_target_overlap, return_strength
from lidar_analysis.physics.detection import (
    AnalyticalModel,
    AssumptionModel,
    DatasheetModel,
    insufficient_data_result,
)
from lidar_analysis.physics.measurement import MeasurementConfig, MeasurementModel
from lidar_analysis.models.common import ErrorDefinition, ConfidenceLevel
from lidar_analysis.scan.scanners import (
    MechanicalSpinningScanner,
    StructuredRasterScanner,
    Channel,
    ScanPoint,
)
from lidar_analysis.simulation.engine import SingleTrialEngine
from lidar_analysis.simulation.monte_carlo import MonteCarloEngine
from lidar_analysis.simulation.analysis import classify, distance_sweep, find_effective_ranges
from lidar_analysis.analysis.suitability import evaluate_suitability, to_suitability_result
from lidar_analysis.analysis.metrics import compute_secondary_metrics
from lidar_analysis.models.application_profile import (
    ApplicationProfile,
    OperationalRange,
    Requirements,
    TargetSpec,
)
from lidar_analysis.models.common import Suitability
from lidar_analysis.reporting import (
    export_json,
    export_csv,
    generate_markdown_report,
    distance_sweep_to_csv,
)
import json
import csv
import io


class TestLevel2IdealTarget:
    """PRD §64 Level 2: Ideal target produces returns per configured model."""

    def test_large_target_normal_incidence(self):
        """Large target at normal incidence, close range, P_d=1 → all detected."""
        target = Cylinder.from_dbh(1.0, [5, 0, 0], [0, 0, 1], 0.9)
        cfg = MeasurementConfig(bias=0.0, sigma=0.01)
        mm = MeasurementModel(range_config=cfg, angular_config=cfg)
        engine = SingleTrialEngine(
            target=target,
            detection_model=AssumptionModel(assumed_probability=1.0),
            measurement_model=mm,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        # Aim directly at target
        sp = ScanPoint(
            horizontal_angle=0.0, vertical_angle=0.0,
            channel_index=0, time=0.0,
            direction=direction_from_angles(0.0, 0.0),
        )
        result = engine.run([sp], np.array([0, 0, 0.0]))
        assert result.hits >= 1
        assert result.detections == result.hits
        for rec in result.detected_records:
            assert rec.measurement is not None
            assert abs(rec.measurement.measured_range - 5.0) < 1.0


class TestLevel2NoIntersection:
    """PRD §64 Level 2: No intersection → zero detections."""

    def test_ray_misses_target(self):
        target = Cylinder.from_dbh(0.10, [30, 0, 0], [0, 0, 1], 0.3)
        cfg = MeasurementConfig(bias=0.0, sigma=0.02)
        mm = MeasurementModel(range_config=cfg, angular_config=cfg)
        engine = SingleTrialEngine(
            target=target,
            detection_model=AssumptionModel(assumed_probability=1.0),
            measurement_model=mm,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        # Aim 90° away from target
        sp = ScanPoint(
            horizontal_angle=math.pi / 2, vertical_angle=0.0,
            channel_index=0, time=0.0,
            direction=direction_from_angles(math.pi / 2, 0.0),
        )
        result = engine.run([sp], np.array([0, 0, 0.0]))
        assert result.hits == 0
        assert result.detections == 0


class TestLevel2ZeroProbability:
    """PRD §64 Level 2: P_d = 0 → zero detections even on hits."""

    def test_pd_zero(self):
        target = Cylinder.from_dbh(0.10, [10, 0, 0], [0, 0, 1], 0.3)
        cfg = MeasurementConfig(bias=0.0, sigma=0.02)
        mm = MeasurementModel(range_config=cfg, angular_config=cfg)
        engine = SingleTrialEngine(
            target=target,
            detection_model=AssumptionModel(assumed_probability=0.0),
            measurement_model=mm,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        sp = ScanPoint(
            horizontal_angle=0.0, vertical_angle=0.0,
            channel_index=0, time=0.0,
            direction=direction_from_angles(0.0, 0.0),
        )
        result = engine.run([sp], np.array([0, 0, 0.0]))
        assert result.detections == 0


class TestFullPipeline:
    """End-to-end: sensor → scan → intersection → detection → MC → analysis → report."""

    def test_full_pipeline(self):
        # 1. Target
        target = Cylinder.from_dbh(0.10, [20, 0, 0], [0, 0, 1], 0.3)

        # 2. Scanner
        scanner = MechanicalSpinningScanner(
            horizontal_fov=math.radians(30),
            vertical_fov=math.radians(10),
            channels=[Channel(elevation_angle=0.0), Channel(elevation_angle=math.radians(5))],
            point_rate=10000,
            rotation_frequency=10,
        )
        scan_points = scanner.generate_scan_points(duration=0.1)
        assert len(scan_points) > 0

        # 3. Detection model
        det_model = AnalyticalModel(strength_threshold=1e-5, sigmoid_steepness=10000, max_range=100)

        # 4. Measurement model
        mm = MeasurementModel(
            range_config=MeasurementConfig(bias=0.0, sigma=0.02),
            angular_config=MeasurementConfig(bias=0.0, sigma=0.001),
        )

        # 5. Single trial
        engine = SingleTrialEngine(
            target=target,
            detection_model=det_model,
            measurement_model=mm,
            beam_divergence=0.003,
            rng=np.random.default_rng(42),
        )
        trial = engine.run(scan_points, np.array([0, 0, 0.0]))
        assert trial.total_rays == len(scan_points)
        assert trial.hits >= 0

        # 6. Monte Carlo
        mc = MonteCarloEngine(engine, n_trials=50, seed=42)
        mc_result = mc.run(scan_points, np.array([0, 0, 0.0]))
        assert mc_result.n_trials == 50
        assert 0 <= mc_result.p_detected <= 1

        # 7. Classification
        cls = classify(mc_result)
        assert isinstance(cls.detected, bool)

        # 8. Secondary metrics
        metrics = compute_secondary_metrics(
            target_diameter=0.10,
            range_to_target=20.0,
            beam_divergence=0.003,
            n_hits=mc_result.detection_count_stats.mean,
            incidence_angle_rad=0.0,
        )
        assert metrics.target_angular_size_rad > 0

        # 9. Suitability
        profile = ApplicationProfile(
            profile_id="e2e-001",
            name="E2E Test Profile",
            target=TargetSpec(minimum_dbh=0.05, maximum_dbh=1.0),
            operational_range=OperationalRange(minimum=5, maximum=50),
            requirements=Requirements(
                minimum_detection_probability=0.0,
                minimum_reliable_probability=0.0,
                minimum_coverage=0.0,
                maximum_range_uncertainty=10.0,
            ),
        )
        eval_result = evaluate_suitability(profile, mc_result)
        assert eval_result.suitability in list(Suitability)

        sr = to_suitability_result(eval_result)
        assert sr.classification in list(Suitability)

        # 10. Report
        report = generate_markdown_report(
            title="E2E Integration Test Report",
            sensor_info={"model": "Test Sensor"},
            target_info={"type": "cylinder", "dbh": 0.10, "distance": 20},
            results={
                "p_detected": mc_result.p_detected,
                "p_reliable": mc_result.p_reliable,
                "p_characterized": mc_result.p_characterized,
            },
            limitations=["Synthetic test scenario"],
            assumptions=["Clear atmosphere", "P_d from analytical model"],
            conclusions="Sensor detected target under test conditions.",
        )
        assert "# E2E Integration Test Report" in report
        assert "## 14. Conclusions" in report
        assert "Synthetic test scenario" in report

    def test_distance_sweep_e2e(self):
        """Distance sweep end-to-end: sweep 10-50m, find detection range."""
        def factory(dist):
            target = Cylinder.from_dbh(0.10, [dist, 0, 0], [0, 0, 1], 0.3)
            cfg = MeasurementConfig(bias=0.0, sigma=0.02)
            mm = MeasurementModel(range_config=cfg, angular_config=cfg)
            return SingleTrialEngine(
                target=target,
                detection_model=DatasheetModel(max_range=40),
                measurement_model=mm,
                beam_divergence=0.003,
                rng=np.random.default_rng(42),
            )

        sp = ScanPoint(
            horizontal_angle=0.0, vertical_angle=0.0,
            channel_index=0, time=0.0,
            direction=direction_from_angles(0.0, 0.0),
        )
        distances = np.array([10, 20, 30, 50])
        sweep = distance_sweep(
            engine_factory=factory,
            distances=distances,
            n_trials=20,
            seed=42,
            scan_points=[sp],
            sensor_position=np.array([0, 0, 0.0]),
        )
        ranges = find_effective_ranges(sweep)
        assert ranges.detection_range >= 0

        # Export sweep as CSV
        sweep_dict = {
            "distances": [
                {"distance": p.distance, "p_detected": p.p_detected, "p_reliable": p.p_reliable,
                 "p_characterized": p.p_characterized, "expected_returns": p.expected_returns}
                for p in sweep.points
            ]
        }
        csv_str = distance_sweep_to_csv(sweep_dict)
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 5  # header + 4 distances

    def test_monte_carlo_determinism(self):
        """Same seed → identical results across runs."""
        target = Cylinder.from_dbh(0.10, [15, 0, 0], [0, 0, 1], 0.3)
        cfg = MeasurementConfig(bias=0.0, sigma=0.02)
        mm = MeasurementModel(range_config=cfg, angular_config=cfg)
        sp = ScanPoint(
            horizontal_angle=0.0, vertical_angle=0.0,
            channel_index=0, time=0.0,
            direction=direction_from_angles(0.0, 0.0),
        )

        def run_mc(seed):
            engine = SingleTrialEngine(
                target=target,
                detection_model=DatasheetModel(max_range=50),
                measurement_model=mm,
                beam_divergence=0.003,
                rng=np.random.default_rng(seed),
            )
            mc = MonteCarloEngine(engine, n_trials=30, seed=seed)
            return mc.run([sp], np.array([0, 0, 0.0]))

        r1 = run_mc(999)
        r2 = run_mc(999)
        np.testing.assert_array_equal(r1.detection_counts, r2.detection_counts)
        np.testing.assert_array_equal(r1.hit_counts, r2.hit_counts)

    def test_insufficient_data_returns_none(self):
        """PRD §32: insufficient data → P_d = None, never fabricated."""
        result = insufficient_data_result()
        assert result.probability is None
        assert result.physical_model_confidence == ConfidenceLevel.INSUFFICIENT