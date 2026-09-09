"""Simulation engine: single-trial, Monte Carlo, analysis, and modes.

PRD sections 35-54.
"""

from .analysis import (
    Classification,
    DistanceSweepPoint,
    DistanceSweepResult,
    EffectiveRanges,
    classify,
    distance_sweep,
    find_effective_ranges,
)
from .analytical import AnalyticalResult, run_analytical
from .engine import HitRecord, SingleTrialEngine, TrialResult
from .monte_carlo import MonteCarloEngine, MonteCarloResult, MonteCarloStats
from .pointcloud import PointCloudResult, generate_point_cloud

__all__ = [
    "SingleTrialEngine",
    "TrialResult",
    "HitRecord",
    "MonteCarloEngine",
    "MonteCarloResult",
    "MonteCarloStats",
    "Classification",
    "DistanceSweepPoint",
    "DistanceSweepResult",
    "EffectiveRanges",
    "classify",
    "distance_sweep",
    "find_effective_ranges",
    "AnalyticalResult",
    "run_analytical",
    "PointCloudResult",
    "generate_point_cloud",
]