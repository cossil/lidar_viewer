"""Synthetic Point Cloud simulation mode (PRD section 54).

Purpose: spatial analysis, geometric inspection, visualization,
point-distribution evaluation.

Shares the same SingleTrialEngine as the other modes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from ..scan.scanners import ScanPoint
from .engine import SingleTrialEngine


@dataclass
class PointCloudResult:
    """Detected points of a single deterministic scan, as (azimuth, elevation, range)."""

    points: List[List[float]] = field(default_factory=list)

    @property
    def point_count(self) -> int:
        return len(self.points)

    @property
    def as_array(self) -> np.ndarray:
        if not self.points:
            return np.empty((0, 3))
        return np.asarray(self.points, dtype=float)


def generate_point_cloud(
    engine: SingleTrialEngine,
    scan_points: List[ScanPoint],
    sensor_position: np.ndarray,
) -> PointCloudResult:
    """Run one deterministic scan and return the detected points.

    Point range = measured_range when available, else the true range.
    """
    engine.rng = np.random.default_rng(seed=0)
    trial = engine.run(scan_points, sensor_position)

    cloud = []
    for rec in trial.detected_records:
        _r = rec.measurement.measured_range if (
            rec.measurement is not None
            and getattr(rec.measurement, "measured_range", None) is not None
        ) else rec.intersection.distance
        cloud.append([
            float(rec.scan_point.horizontal_angle),
            float(rec.scan_point.vertical_angle),
            float(_r),
        ])
    return PointCloudResult(points=cloud)