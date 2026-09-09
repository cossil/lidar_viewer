"""Target angular size, incidence angle, and beam footprint.

PRD sections 19, 25, 27:
  - θ_T = 2 atan(D / (2R))     (angular size of cylinder diameter D at range R)
  - d_b = 2R tan(θ_b / 2)      (beam diameter at range R)
  - α = acos(|n · (-d)|)       (incidence angle, clamped 0..pi/2)
"""

from __future__ import annotations

import numpy as np


def target_angular_size(diameter: float, range_to_target: float) -> float:
    """Angular size (radians) of a cylinder of *diameter* at *range_to_target*.

    PRD section 19: θ_T = 2 * atan(D / (2 * R))
    """
    if range_to_target <= 0:
        raise ValueError("range must be > 0")
    if diameter <= 0:
        raise ValueError("diameter must be > 0")
    return float(2.0 * np.arctan(diameter / (2.0 * range_to_target)))


def target_angular_size_small_angle(diameter: float, range_to_target: float) -> float:
    """Small-angle approximation: θ_T ≈ D / R."""
    if range_to_target <= 0:
        raise ValueError("range must be > 0")
    return float(diameter / range_to_target)


def beam_footprint(range_to_target: float, beam_divergence: float) -> float:
    """Beam diameter at *range_to_target* (radians divergence).

    PRD section 25: d_b = 2 * R * tan(θ_b / 2)
    """
    if range_to_target <= 0:
        raise ValueError("range must be > 0")
    if beam_divergence < 0:
        raise ValueError("beam_divergence must be >= 0")
    return float(2.0 * range_to_target * np.tan(beam_divergence / 2.0))


def beam_footprint_small_angle(range_to_target: float, beam_divergence: float) -> float:
    """Small-angle approximation: d_b ≈ R * θ_b."""
    if range_to_target <= 0:
        raise ValueError("range must be > 0")
    return float(range_to_target * beam_divergence)


def incidence_angle(
    surface_normal: np.ndarray,
    ray_direction: np.ndarray,
) -> float:
    """Incidence angle (radians) between surface normal and incoming ray.

    PRD section 27: α = acos(|n · (-d)|), clamped to [0, pi/2].
    """
    n = np.asarray(surface_normal, dtype=np.float64)
    d = np.asarray(ray_direction, dtype=np.float64)
    n_norm = np.linalg.norm(n)
    d_norm = np.linalg.norm(d)
    if n_norm < 1e-15 or d_norm < 1e-15:
        raise ValueError("vectors must be non-zero")
    n = n / n_norm
    d = d / d_norm
    cos_alpha = abs(np.dot(n, -d))
    cos_alpha = np.clip(cos_alpha, 0.0, 1.0)
    return float(np.arccos(cos_alpha))