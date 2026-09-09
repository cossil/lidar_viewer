"""Beam/target overlap and return strength model.

PRD section 26: G in [0,1] — overlap between beam footprint and target.
PRD section 29: S proportional to rho * A_eff * cos(alpha) / R^2.
"""

from __future__ import annotations

import numpy as np

from ..geometry.angular_size import beam_footprint


def beam_target_overlap(
    target_diameter: float,
    beam_diameter: float,
) -> float:
    """Analytical beam/target overlap fraction G in [0, 1].

    MVP (PRD section 26): ratio of target diameter to beam diameter,
    clamped to [0, 1]. Assumes coaxial alignment.
    """
    if beam_diameter <= 0:
        return 0.0
    return float(np.clip(target_diameter / beam_diameter, 0.0, 1.0))


def return_strength(
    reflectivity: float,
    effective_area: float,
    incidence_angle: float,
    range_to_target: float,
) -> float:
    """Simplified return strength proxy (PRD section 29).

    S ∝ ρ * A_eff * cos(α) / R²

    This is a physics-inspired engineering approximation, not a universal
    LiDAR equation. Returns 0 for invalid inputs.
    """
    if range_to_target <= 0 or effective_area <= 0:
        return 0.0
    cos_alpha = np.cos(np.clip(incidence_angle, 0, np.pi / 2))
    return float(reflectivity * effective_area * cos_alpha / (range_to_target ** 2))


def effective_illuminated_area_cylinder(
    beam_diameter: float,
    target_diameter: float,
    incidence_angle: float,
    target_length: float = float("inf"),
) -> float:
    """Effective illuminated area on a cylindrical target.

    The illuminated strip width is min(beam_diameter, target_diameter).
    The length is limited by the beam sweep or target length.
    cos(α) accounts for the incidence angle.
    """
    width = min(beam_diameter, target_diameter)
    length = min(target_length, beam_diameter) if target_length < float("inf") else beam_diameter
    cos_alpha = np.cos(np.clip(incidence_angle, 0, np.pi / 2))
    if cos_alpha < 1e-12:
        return 0.0
    return float(width * length / cos_alpha)