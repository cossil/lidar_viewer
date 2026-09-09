"""Post-simulation analysis: classification, effective ranges, sweeps.

PRD sections 39-44.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from .monte_carlo import MonteCarloEngine, MonteCarloResult
from .engine import SingleTrialEngine


def geometric_coverage(detected_angles, hit_angles):
    """C_g = A_covered / A_visible via angular bounding boxes (PRD 40).

    detected_angles: list of (azim, elev) for DETECTED hits.
    hit_angles: list of (azim, elev) for ALL hits.
    Returns 0.0 if no hits; 1.0 if visible area is 0.
    """
    if not hit_angles:
        return 0.0

    def bbox_area(pts):
        if not pts:
            return 0.0
        az = [p[0] for p in pts]
        el = [p[1] for p in pts]
        return (max(az) - min(az)) * (max(el) - min(el))

    A_vis = bbox_area(hit_angles)
    if A_vis <= 0:
        return 1.0
    return min(1.0, bbox_area(detected_angles) / A_vis)


@dataclass
class Classification:
    """Detection classification (PRD section 39).

    Three levels: DETECTED, RELIABLE, CHARACTERIZED.
    """

    detected: bool
    reliable: bool
    characterized: bool
    p_detected: float
    p_reliable: float
    p_characterized: float


@dataclass
class DistanceSweepPoint:
    """Result at a single distance in a distance sweep (PRD section 43)."""

    distance: float
    p_detected: float
    p_reliable: float
    p_characterized: float
    expected_returns: float


@dataclass
class DistanceSweepResult:
    """Result of a distance sweep."""

    distances: np.ndarray
    points: List[DistanceSweepPoint]


@dataclass
class EffectiveRanges:
    """Effective ranges (PRD section 42).

    R_characterization ≤ R_reliable ≤ R_detection
    """

    detection_range: float
    reliable_range: float
    characterization_range: float


def classify(
    mc_result: MonteCarloResult,
    min_returns_detected: int = 1,
    min_returns_reliable: int = 5,
    min_returns_characterized: int = 10,
    min_coverage: float = 0.3,
    sigma_R_threshold: float = 0.1,
    detection_threshold: float = 0.5,
    reliable_threshold: float = 0.9,
    characterized_threshold: float = 0.9,
) -> Classification:
    """Classify detection level (PRD section 39).

    CHARACTERIZED now depends on mc_result.p_characterized, which already folds
    in detection count, geometric coverage C_g, and per-trial sigma_R (PRD 39-41).
    When coverages is None (backward-compat, hand-built result) p_characterized is
    the count-only value, so this remains correct without extra logic here.
    """
    return Classification(
        detected=mc_result.p_detected >= detection_threshold,
        reliable=mc_result.p_reliable >= reliable_threshold,
        characterized=mc_result.p_characterized >= characterized_threshold,
        p_detected=mc_result.p_detected,
        p_reliable=mc_result.p_reliable,
        p_characterized=mc_result.p_characterized,
    )


def distance_sweep(
    engine_factory,
    distances: np.ndarray,
    n_trials: int = 1000,
    seed: int = 42,
    **mc_kwargs,
) -> DistanceSweepResult:
    """Run Monte Carlo at each distance (PRD section 43).

    Args:
        engine_factory: Callable(distance) -> SingleTrialEngine
        distances: Array of distances to sweep.
        n_trials: Number of MC trials per distance.
        seed: Base random seed.
    """
    points = []
    for dist in distances:
        engine = engine_factory(float(dist))
        mc = MonteCarloEngine(engine, n_trials=n_trials, seed=seed)
        result = mc.run(**mc_kwargs)
        points.append(DistanceSweepPoint(
            distance=float(dist),
            p_detected=result.p_detected,
            p_reliable=result.p_reliable,
            p_characterized=result.p_characterized,
            expected_returns=float(np.mean(result.expected_returns)),
        ))

    return DistanceSweepResult(distances=distances, points=points)


def find_effective_ranges(
    sweep: DistanceSweepResult,
    detection_threshold: float = 0.5,
    reliable_threshold: float = 0.9,
    characterized_threshold: float = 0.9,
) -> EffectiveRanges:
    """Extract effective ranges from a distance sweep (PRD section 42).

    Finds the maximum distance where each threshold is met.
    """
    r_det = 0.0
    r_rel = 0.0
    r_char = 0.0

    for p in sweep.points:
        if p.p_detected >= detection_threshold:
            r_det = max(r_det, p.distance)
        if p.p_reliable >= reliable_threshold:
            r_rel = max(r_rel, p.distance)
        if p.p_characterized >= characterized_threshold:
            r_char = max(r_char, p.distance)

    return EffectiveRanges(
        detection_range=r_det,
        reliable_range=r_rel,
        characterization_range=r_char,
    )