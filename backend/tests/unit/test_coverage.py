"""Geometric coverage C_g and sigma_R folding into CHARACTERIZED (PRD 39-41).

Tests:
  - geometric_coverage: concentrated vs distributed detected bbox
  - edge cases: no hits, zero visible area
  - classify() CHARACTERIZED respects coverage + sigma via p_characterized
  - MonteCarloEngine p_characterized folds coverage, count, and sigma_R
  - backward-compat classify without coverage arrays
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from lidar_analysis.geometry.targets import Cylinder
from lidar_analysis.geometry.rays import direction_from_angles
from lidar_analysis.physics.detection import AssumptionModel
from lidar_analysis.physics.measurement import MeasurementConfig, MeasurementModel
from lidar_analysis.models.common import ErrorDefinition
from lidar_analysis.scan.scanners import ScanPoint
from lidar_analysis.simulation.engine import SingleTrialEngine
from lidar_analysis.simulation.monte_carlo import MonteCarloEngine, MonteCarloResult
from lidar_analysis.simulation.analysis import classify, geometric_coverage


def _make_scan_point(h: float = 0.0, v: float = 0.0) -> ScanPoint:
    return ScanPoint(
        horizontal_angle=h,
        vertical_angle=v,
        channel_index=0,
        time=0.0,
        direction=direction_from_angles(h, v),
    )


def _measurement_model(sigma: float = 0.02) -> MeasurementModel:
    cfg = MeasurementConfig(bias=0.0, sigma=sigma, error_definition=ErrorDefinition.ONE_SIGMA)
    return MeasurementModel(range_config=cfg, angular_config=cfg)


def _cov_result(coverages, sigma=None) -> MonteCarloResult:
    """Hand-built result whose p_characterized folds coverage + sigma (PRD 41)."""
    coverages = np.asarray(coverages, dtype=float)
    n = coverages.size
    counts = np.full(n, 12)  # all trials meet min_returns_characterized
    sigma = np.full(n, 0.01) if sigma is None else np.asarray(sigma, dtype=float)
    pass_mask = (counts >= 10) & (coverages >= 0.3) & (sigma <= 0.1)
    return MonteCarloResult(
        n_trials=n,
        seed=1,
        detection_counts=counts,
        hit_counts=counts,
        expected_returns=np.full(n, 12.0),
        detection_count_stats=None,
        expected_returns_stats=None,
        p_detected=1.0,
        p_reliable=1.0,
        p_characterized=float(np.mean(pass_mask)),
        coverages=coverages,
        sigma_R_values=sigma,
    )


def test_coverage_concentrated_vs_distributed():
    """PRD 40: 10 concentrated points cover far less area than 10 spread points."""
    # visible target subtends a 1.0 x 1.0 angular region (area = 1.0)
    hit = [(h, v) for h in (-0.5, 0.5) for v in (-0.5, 0.5)]
    concentrated = [((i % 4) * 0.002, (i // 4) * 0.002) for i in range(10)]
    distributed = [(-0.45 + i * 0.1, -0.45 + i * 0.1) for i in range(10)]
    cov_conc = geometric_coverage(concentrated, hit)
    cov_dist = geometric_coverage(distributed, hit)
    assert cov_dist > cov_conc
    assert cov_dist <= 1.0
    assert cov_conc < 0.05


def test_coverage_no_hits_zero():
    assert geometric_coverage([], []) == 0.0


def test_coverage_visible_zero_one():
    # visible bbox is a point -> by convention full coverage
    assert geometric_coverage([(0.0, 0.0)], [(0.0, 0.0)]) == 1.0
    # detected area == visible area -> coverage 1
    pts = [(h, 0.0) for h in np.linspace(-0.5, 0.5, 9)]
    assert geometric_coverage(pts, pts) == 1.0


def test_classify_characterized_respects_coverage_and_sigma():
    """Low coverage must flip CHARACTERIZED off via the folded p_characterized."""
    low = _cov_result(np.full(50, 0.1))       # all trials coverage < 0.3
    high = _cov_result(np.full(50, 0.9))      # coverage >= 0.3, sigma low
    # count-only would have given p_characterized = 1.0; coverage folds to 0.0
    assert low.p_detected == 1.0
    assert low.p_reliable == 1.0
    assert low.p_characterized == 0.0          # coverage gating drops every trial
    assert classify(low).characterized is False
    assert classify(high).characterized is True

    # sigma_R gating: high sigma_R drops p below threshold
    noisy = _cov_result(np.full(50, 0.9), sigma=np.full(50, 0.5))
    assert noisy.p_characterized == 0.0
    assert classify(noisy).characterized is False


def test_p_characterized_folds_in_coverage():
    """p_characterized equals mean(count & coverage & sigma) over arrays."""
    target = Cylinder.from_dbh(0.30, [10, 0, 0], [0, 0, 1], 1.0)
    mm = _measurement_model()
    engine = SingleTrialEngine(
        target=target,
        detection_model=AssumptionModel(assumed_probability=1.0),
        measurement_model=mm,
        beam_divergence=0.003,
        rng=np.random.default_rng(42),
    )
    # 12 scan points at target center so all detections concentrate on target
    scan_points = [_make_scan_point(h=math.radians(i * 0.3), v=0.0) for i in range(12)]
    mc = MonteCarloEngine(engine, n_trials=30, seed=42)
    result = mc.run(scan_points, np.array([0, 0, 0.0]),
                    min_returns_characterized=10,
                    min_coverage_characterized=0.3,
                    sigma_R_threshold=0.1)
    counts = result.detection_counts
    expected = np.mean(
        (counts >= 10)
        & (result.coverages >= 0.3)
        & (result.sigma_R_values <= 0.1)
    )
    assert result.p_characterized == pytest.approx(expected)
    # coverages / sigma arrays were always accumulated even without keep_trials
    assert result.coverages is not None
    assert result.sigma_R_values is not None
    assert len(result.coverages) == 30


def test_classify_backward_compat_without_coverage():
    """coverages=None (count-only) must still classify without crashing."""
    n = 20
    counts = np.full(n, 10)
    result = MonteCarloResult(
        n_trials=n,
        seed=1,
        detection_counts=counts,
        hit_counts=counts,
        expected_returns=np.full(n, 10.0),
        detection_count_stats=None,
        expected_returns_stats=None,
        p_detected=1.0,
        p_reliable=1.0,
        p_characterized=1.0,
        coverages=None,
        sigma_R_values=None,
    )
    cls = classify(result)
    assert cls.characterized is True
    assert isinstance(cls.p_characterized, float)