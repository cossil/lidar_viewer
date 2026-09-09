"""Ray generation utilities.

PRD section 17: r(t) = P_L + t * d, where d is a unit direction vector.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def make_ray(origin: NDArray[np.float64], direction: NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Create a normalised ray (origin, unit direction).

    Raises ValueError if direction is zero-length.
    """
    o = np.asarray(origin, dtype=np.float64)
    d = np.asarray(direction, dtype=np.float64)
    norm = np.linalg.norm(d)
    if norm < 1e-15:
        raise ValueError("ray direction must be non-zero")
    return o, d / norm


def ray_at(t: float, origin: NDArray[np.float64], direction: NDArray[np.float64]) -> NDArray[np.float64]:
    """Evaluate the ray at parameter t: P = origin + t * direction."""
    return np.asarray(origin) + t * np.asarray(direction)


def direction_from_angles(horizontal_angle: float, vertical_angle: float) -> NDArray[np.float64]:
    """Unit direction vector from horizontal and vertical angles (radians).

    horizontal_angle: azimuth from +X toward +Y in the XY plane.
    vertical_angle: elevation from the XY plane toward +Z.
    """
    ch, sh = np.cos(horizontal_angle), np.sin(horizontal_angle)
    cv, sv = np.cos(vertical_angle), np.sin(vertical_angle)
    return np.array([ch * cv, sh * cv, sv], dtype=np.float64)


def generate_mechanical_spin_directions(
    horizontal_fov: float,
    vertical_fov: float,
    horizontal_resolution: float,
    vertical_resolution: float,
) -> NDArray[np.float64]:
    """Generate candidate ray directions for a mechanical spinning scanner.

    Returns an (N, 3) array of unit direction vectors in the sensor frame.
    Centered at horizontal_angle=0, vertical_angle=0.
    """
    h_angles = np.arange(-horizontal_fov / 2, horizontal_fov / 2, horizontal_resolution)
    v_angles = np.arange(-vertical_fov / 2, vertical_fov / 2, vertical_resolution)

    directions = []
    for v in v_angles:
        for h in h_angles:
            directions.append(direction_from_angles(h, v))
    return np.array(directions, dtype=np.float64)