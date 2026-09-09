"""Analytical (deterministic) simulation mode (PRD section 54).

Purpose: fast evaluation, broad parameter sweeps, preliminary trade studies.
Characteristics: deterministic, fast, limited stochastic detail.

Shares the same underlying SingleTrialEngine as Monte Carlo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from ..scan.scanners import ScanPoint
from .engine import SingleTrialEngine, TrialResult


@dataclass
class AnalyticalResult:
    """Deterministic analytical result for a single scan."""

    expected_returns: float
    expected_detections: float
    coverage: float
    range_uncertainty: Optional[float]
    trial: TrialResult


def _trial_coverage(trial: TrialResult) -> float:
    """C_g of one trial via angular bounding boxes (reuses PRD 40 semantics)."""
    from .analysis import geometric_coverage

    detected = [(r.scan_point.horizontal_angle, r.scan_point.vertical_angle)
                for r in trial.detected_records]
    hits = [(r.scan_point.horizontal_angle, r.scan_point.vertical_angle)
            for r in trial.hit_records]
    return geometric_coverage(detected, hits)


def _trial_range_uncertainty(trial: TrialResult) -> Optional[float]:
    """Sample std of measured ranges among detected records; None if <2 values."""
    ranges = [r.measurement.measured_range for r in trial.detected_records
              if r.measurement is not None and getattr(r.measurement, "measured_range", None)
              is not None]
    if len(ranges) < 2:
        return None
    return float(np.std(ranges))


def run_analytical(
    engine: SingleTrialEngine,
    scan_points: List[ScanPoint],
    sensor_position: np.ndarray,
) -> AnalyticalResult:
    """Run one deterministic trial and expose expected values.

    Uses a fixed seed so repeated calls are bit-identical (deterministic).
    """
    engine.rng = np.random.default_rng(seed=0)
    trial = engine.run(scan_points, sensor_position)
    return AnalyticalResult(
        expected_returns=float(trial.expected_returns),
        expected_detections=float(trial.detections),
        coverage=_trial_coverage(trial),
        range_uncertainty=_trial_range_uncertainty(trial),
        trial=trial,
    )