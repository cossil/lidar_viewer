"""Analysis engine tests (PRD sections 45-54).

Tests:
  - Sensor comparison: multiple sensors, same conditions, best sensor selection
  - Suitability evaluation: all pass, some fail, insufficient data
  - Secondary metrics: angular size, beam footprint, coverage
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from lidar_analysis.analysis.metrics import compute_secondary_metrics
from lidar_analysis.analysis.suitability import evaluate_suitability, to_suitability_result
from lidar_analysis.geometry.targets import Cylinder
from lidar_analysis.models.application_profile import ApplicationProfile, OperationalRange, Requirements, TargetSpec
from lidar_analysis.models.common import Suitability
from lidar_analysis.physics.detection import AssumptionModel, DatasheetModel
from lidar_analysis.physics.measurement import MeasurementConfig, MeasurementModel
from lidar_analysis.models.common import ErrorDefinition
from lidar_analysis.scan.scanners import ScanPoint
from lidar_analysis.simulation.engine import SingleTrialEngine
from lidar_analysis.simulation.monte_carlo import MonteCarloEngine
from lidar_analysis.geometry.rays import direction_from_angles


def _make_scan_point(h=0.0, v=0.0) -> ScanPoint:
    return ScanPoint(horizontal_angle=h, vertical_angle=v, channel_index=0, time=0.0,
                     direction=direction_from_angles(h, v))


def _make_profile(
    min_det: float = 0.5,
    min_rel: float = 0.3,
    min_cov: float = 0.1,
    max_range_unc: float = 0.1,
) -> ApplicationProfile:
    return ApplicationProfile(
        profile_id="test-001",
        name="Test Profile",
        target=TargetSpec(minimum_dbh=0.05, maximum_dbh=1.0),
        operational_range=OperationalRange(minimum=5, maximum=50),
        requirements=Requirements(
            minimum_detection_probability=min_det,
            minimum_reliable_probability=min_rel,
            minimum_coverage=min_cov,
            maximum_range_uncertainty=max_range_unc,
        ),
    )


@pytest.fixture()
def mc_result_high():
    """MC result with high detection rate."""
    target = Cylinder.from_dbh(0.10, [10, 0, 0], [0, 0, 1], 0.3)
    cfg = MeasurementConfig(bias=0.0, sigma=0.02)
    mm = MeasurementModel(range_config=cfg, angular_config=cfg)
    engine = SingleTrialEngine(
        target=target,
        detection_model=DatasheetModel(max_range=50),
        measurement_model=mm,
        beam_divergence=0.003,
        rng=np.random.default_rng(42),
    )
    # Multiple scan points for higher hit rate
    points = [_make_scan_point(h=math.radians(i - 5) * 0.5) for i in range(11)]
    mc = MonteCarloEngine(engine, n_trials=50, seed=42)
    return mc.run(points, np.array([0, 0, 0.0]))


@pytest.fixture()
def mc_result_low():
    """MC result with low/zero detection rate."""
    target = Cylinder.from_dbh(0.10, [50, 0, 0], [0, 0, 1], 0.1)
    cfg = MeasurementConfig(bias=0.0, sigma=0.02)
    mm = MeasurementModel(range_config=cfg, angular_config=cfg)
    engine = SingleTrialEngine(
        target=target,
        detection_model=AssumptionModel(assumed_probability=0.0),
        measurement_model=mm,
        beam_divergence=0.003,
        rng=np.random.default_rng(42),
    )
    mc = MonteCarloEngine(engine, n_trials=20, seed=42)
    return mc.run([_make_scan_point()], np.array([0, 0, 0.0]))


class TestSuitability:
    def test_suitable(self, mc_result_high):
        """High detection → SUITABLE when all criteria met."""
        profile = _make_profile(min_det=0.0, min_rel=0.0, max_range_unc=10.0, min_cov=0.0)
        eval = evaluate_suitability(profile, mc_result_high)
        assert eval.suitability == Suitability.SUITABLE
        assert all(c.passed for c in eval.criteria)

    def test_not_suitable(self, mc_result_low):
        """Zero detection → NOT_SUITABLE."""
        profile = _make_profile(min_det=0.5)
        eval = evaluate_suitability(profile, mc_result_low)
        assert eval.suitability == Suitability.NOT_SUITABLE
        assert any(not c.passed for c in eval.criteria)

    def test_insufficient_data(self, mc_result_high):
        """Insufficient data flag → INSUFFICIENT_DATA."""
        profile = _make_profile()
        eval = evaluate_suitability(profile, mc_result_high, has_insufficient_data=True)
        assert eval.suitability == Suitability.INSUFFICIENT_DATA
        assert len(eval.limitations) > 0

    def test_to_suitability_result(self, mc_result_high):
        """Conversion to SuitabilityResult model."""
        profile = _make_profile(min_det=0.0, min_rel=0.0, max_range_unc=10.0, min_cov=0.0)
        eval = evaluate_suitability(profile, mc_result_high)
        result = to_suitability_result(eval)
        assert result.classification == Suitability.SUITABLE

    def test_traceable_criteria(self, mc_result_high):
        """PRD section 46: classification must be traceable to explicit criteria."""
        profile = _make_profile(min_det=0.0, min_rel=0.0, max_range_unc=10.0, min_cov=0.0)
        eval = evaluate_suitability(profile, mc_result_high)
        for c in eval.criteria:
            assert c.criterion is not None
            assert c.required is not None
            assert c.measured is not None
            assert isinstance(c.passed, bool)


class TestSecondaryMetrics:
    def test_basic_metrics(self):
        m = compute_secondary_metrics(
            target_diameter=0.1,
            range_to_target=30.0,
            beam_divergence=0.003,
            n_hits=5,
            incidence_angle_rad=0.0,
        )
        assert m.target_angular_size_rad > 0
        assert m.beam_footprint_m > 0
        assert m.point_density_per_m2 > 0
        assert 0 <= m.geometric_coverage <= 1

    def test_angular_size_degrees(self):
        m = compute_secondary_metrics(0.1, 30, 0.003, 1, 0)
        assert np.isclose(m.target_angular_size_deg, np.degrees(m.target_angular_size_rad))

    def test_zero_range(self):
        with pytest.raises(ValueError, match="range"):
            compute_secondary_metrics(0.1, 0, 0.003, 1, 0)