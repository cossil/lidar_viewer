"""Secondary metrics computation (PRD section 49).

Computes analysis dashboard metrics:
  target angular size, beam footprint, incidence angle, point density, coverage.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..geometry.angular_size import target_angular_size, beam_footprint, incidence_angle


@dataclass
class SecondaryMetrics:
    """Secondary analysis metrics (PRD section 49)."""

    target_angular_size_rad: float
    target_angular_size_deg: float
    beam_footprint_m: float
    incidence_angle_rad: float
    incidence_angle_deg: float
    point_density_per_m2: float
    geometric_coverage: float


def compute_secondary_metrics(
    target_diameter: float,
    range_to_target: float,
    beam_divergence: float,
    n_hits: int,
    incidence_angle_rad: float,
) -> SecondaryMetrics:
    """Compute secondary metrics for analysis dashboard."""
    theta_t = target_angular_size(target_diameter, range_to_target)
    d_b = beam_footprint(range_to_target, beam_divergence)
    alpha = np.clip(incidence_angle_rad, 0, np.pi / 2)

    # Point density: hits per unit area of beam footprint
    beam_area = np.pi * (d_b / 2) ** 2 if d_b > 0 else 1.0
    density = n_hits / beam_area if beam_area > 0 else 0.0

    # Geometric coverage approximation: target area / beam area, clamped
    target_area = np.pi * (target_diameter / 2) ** 2
    coverage = min(target_area / beam_area, 1.0) if beam_area > 0 else 0.0

    return SecondaryMetrics(
        target_angular_size_rad=theta_t,
        target_angular_size_deg=float(np.degrees(theta_t)),
        beam_footprint_m=d_b,
        incidence_angle_rad=float(alpha),
        incidence_angle_deg=float(np.degrees(alpha)),
        point_density_per_m2=density,
        geometric_coverage=coverage,
    )