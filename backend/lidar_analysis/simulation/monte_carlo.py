"""Monte Carlo simulation wrapper (PRD sections 37-38).

Runs N trials and collects statistical outputs:
  mean, median, std, min, max, p05, p25, p75, p95.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .engine import SingleTrialEngine, TrialResult
from ..scan.scanners import ScanPoint


@dataclass
class MonteCarloStats:
    """Statistical summary of a Monte Carlo run."""

    mean: float
    median: float
    std: float
    min: float
    max: float
    p05: float
    p25: float
    p75: float
    p95: float


@dataclass
class MonteCarloResult:
    """Result of a Monte Carlo simulation (PRD section 38)."""

    n_trials: int
    seed: int

    # Per-trial arrays
    detection_counts: np.ndarray
    hit_counts: np.ndarray
    expected_returns: np.ndarray

    # Aggregated statistics
    detection_count_stats: MonteCarloStats
    expected_returns_stats: MonteCarloStats

    # Probabilities (fraction of trials meeting criteria)
    p_detected: float
    p_reliable: float
    p_characterized: float

    # Individual trial results (for further analysis)
    trials: List[TrialResult] = field(default_factory=list)

    # Per-trial geometric coverage C_g and range-noise sigma_R (PRD 39-41).
    # None when coverage was not computed (backward-compat).
    coverages: Optional[np.ndarray] = None
    sigma_R_values: Optional[np.ndarray] = None


def _compute_stats(values: np.ndarray) -> MonteCarloStats:
    """Compute summary statistics from an array of values."""
    return MonteCarloStats(
        mean=float(np.mean(values)),
        median=float(np.median(values)),
        std=float(np.std(values)),
        min=float(np.min(values)),
        max=float(np.max(values)),
        p05=float(np.percentile(values, 5)),
        p25=float(np.percentile(values, 25)),
        p75=float(np.percentile(values, 75)),
        p95=float(np.percentile(values, 95)),
    )


class MonteCarloEngine:
    """Runs multiple simulation trials and collects statistics.

    PRD section 37: Default 10,000 trials, configurable 1,000-100,000.
    PRD section 38: Outputs include mean, median, std, min, max, percentiles.
    """

    def __init__(
        self,
        trial_engine: SingleTrialEngine,
        n_trials: int = 10000,
        seed: int = 123456,
    ):
        if not (1 <= n_trials <= 100000):
            raise ValueError("n_trials must be 1-100000")
        self.trial_engine = trial_engine
        self.n_trials = n_trials
        self.seed = seed

    def run(
        self,
        scan_points: List[ScanPoint],
        sensor_position: np.ndarray,
        min_returns_detected: int = 1,
        min_returns_reliable: int = 5,
        min_returns_characterized: int = 10,
        min_coverage_characterized: float = 0.3,
        sigma_R_threshold: float = 0.1,
        reliable_confidence: float = 0.9,
        characterized_confidence: float = 0.9,
        keep_trials: bool = False,
    ) -> MonteCarloResult:
        """Execute Monte Carlo simulation.

        Args:
            scan_points: Pre-generated scan points.
            sensor_position: LiDAR position.
            min_returns_detected: Minimum returns for 'detected' classification.
            min_returns_reliable: Minimum returns for 'reliable' classification.
            min_returns_characterized: Minimum returns for 'characterized' classification.
            min_coverage_characterized: Minimum geometric coverage for characterization (PRD 40).
            sigma_R_threshold: Maximum per-trial range-noise std for characterization (PRD 41).
            reliable_confidence: Required probability of meeting reliable criterion.
            characterized_confidence: Required probability of meeting characterization criterion.
            keep_trials: If True, store individual trial results.
        """
        from .analysis import geometric_coverage

        rng = np.random.default_rng(self.seed)

        detection_counts = np.zeros(self.n_trials)
        hit_counts = np.zeros(self.n_trials)
        expected_returns_arr = np.zeros(self.n_trials)
        coverages = np.zeros(self.n_trials)
        sigma_R_values = np.zeros(self.n_trials)
        trials = []

        for i in range(self.n_trials):
            # Each trial gets its own RNG derived from the master seed
            trial_rng = np.random.default_rng(self.seed + i)
            self.trial_engine.rng = trial_rng

            result = self.trial_engine.run(scan_points, sensor_position)

            detection_counts[i] = result.detections
            hit_counts[i] = result.hits
            expected_returns_arr[i] = result.expected_returns

            # Geometric coverage C_g = A_covered / A_visible (PRD 40)
            hit_angles = [
                (r.scan_point.horizontal_angle, r.scan_point.vertical_angle)
                for r in result.hit_records
            ]
            det_angles = [
                (r.scan_point.horizontal_angle, r.scan_point.vertical_angle)
                for r in result.detected_records
            ]
            coverages[i] = geometric_coverage(det_angles, hit_angles)

            # Per-trial range-noise sigma_R = std of measured ranges (PRD 41)
            ranges = [
                r.measurement.measured_range for r in result.detected_records
                if r.measurement is not None
            ]
            if len(ranges) >= 2:
                sigma_R_values[i] = float(np.std(ranges))
            else:
                sigma_R_values[i] = np.inf

            if keep_trials:
                trials.append(result)

        # Classification probabilities (PRD sections 39-41)
        p_detected = float(np.mean(detection_counts >= min_returns_detected))
        p_reliable = float(np.mean(detection_counts >= min_returns_reliable))
        p_characterized = float(np.mean(
            (detection_counts >= min_returns_characterized)
            & (coverages >= min_coverage_characterized)
            & (sigma_R_values <= sigma_R_threshold)
        ))

        return MonteCarloResult(
            n_trials=self.n_trials,
            seed=self.seed,
            detection_counts=detection_counts,
            hit_counts=hit_counts,
            expected_returns=expected_returns_arr,
            detection_count_stats=_compute_stats(detection_counts),
            expected_returns_stats=_compute_stats(expected_returns_arr),
            p_detected=p_detected,
            p_reliable=p_reliable,
            p_characterized=p_characterized,
            trials=trials,
            coverages=coverages,
            sigma_R_values=sigma_R_values,
        )