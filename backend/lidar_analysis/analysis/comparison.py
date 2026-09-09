"""Sensor comparison engine (PRD section 45).

Compares multiple sensors under identical conditions:
  same target, DBH, distance, reflectivity, incidence angle, orientation,
  duration, Monte Carlo count, classification criteria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

import numpy as np

from ..simulation.engine import SingleTrialEngine
from ..simulation.monte_carlo import MonteCarloEngine, MonteCarloResult
from ..simulation.analysis import Classification, classify, distance_sweep, find_effective_ranges, EffectiveRanges


@dataclass
class SensorComparisonEntry:
    """Result for a single sensor in a comparison study."""

    sensor_id: str
    mc_result: MonteCarloResult
    classification: Classification
    effective_ranges: EffectiveRanges


@dataclass
class SensorComparisonResult:
    """Result of a multi-sensor comparison (PRD section 45)."""

    entries: List[SensorComparisonEntry]

    def best_sensor(self) -> SensorComparisonEntry:
        """Return the sensor with the highest detection probability."""
        return max(self.entries, key=lambda e: e.mc_result.p_detected)

    def summary(self) -> Dict[str, Dict]:
        """Return a summary dict suitable for serialization."""
        return {
            e.sensor_id: {
                "p_detected": e.mc_result.p_detected,
                "p_reliable": e.mc_result.p_reliable,
                "p_characterized": e.mc_result.p_characterized,
                "expected_returns_mean": e.mc_result.expected_returns_stats.mean,
                "detection_range": e.effective_ranges.detection_range,
                "reliable_range": e.effective_ranges.reliable_range,
                "characterization_range": e.effective_ranges.characterization_range,
                "detected": e.classification.detected,
                "reliable": e.classification.reliable,
                "characterized": e.classification.characterized,
            }
            for e in self.entries
        }


def compare_sensors(
    sensor_ids: List[str],
    engine_factories: Dict[str, Callable[[], SingleTrialEngine]],
    scan_points,
    sensor_position: np.ndarray,
    n_trials: int = 1000,
    seed: int = 42,
    **classify_kwargs,
) -> SensorComparisonResult:
    """Run identical MC simulations for multiple sensors and compare.

    Args:
        sensor_ids: List of sensor identifiers.
        engine_factories: Dict mapping sensor_id -> factory that returns SingleTrialEngine.
        scan_points: Pre-generated scan points (same for all sensors).
        sensor_position: LiDAR position (same for all sensors).
        n_trials: Number of MC trials (same for all sensors).
        seed: Random seed (same for all sensors).
    """
    entries = []
    for sid in sensor_ids:
        engine = engine_factories[sid]()
        mc = MonteCarloEngine(engine, n_trials=n_trials, seed=seed)
        result = mc.run(scan_points, sensor_position)
        cls = classify(result, **classify_kwargs)

        # Effective ranges via distance sweep
        distances = np.linspace(5, 80, 16)

        def _factory(dist, _sid=sid):
            e = engine_factories[_sid]()
            # Override target position
            from ..geometry.targets import Cylinder
            if isinstance(e.target, Cylinder):
                e.target = Cylinder.from_dbh(
                    e.target.diameter, [dist, 0, 0],
                    e.target.axis.tolist(), e.target.reflectivity,
                )
            return e

        sweep = distance_sweep(
            engine_factory=_factory,
            distances=distances,
            n_trials=min(n_trials, 100),
            seed=seed,
            scan_points=scan_points,
            sensor_position=sensor_position,
        )
        ranges = find_effective_ranges(sweep)

        entries.append(SensorComparisonEntry(
            sensor_id=sid,
            mc_result=result,
            classification=cls,
            effective_ranges=ranges,
        ))

    return SensorComparisonResult(entries=entries)