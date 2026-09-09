"""Analytical ray-target intersection (PRD section 18).

Exports:
    ray_cylinder_intersection — infinite lateral cylinder (no endcaps)
    ray_box_intersection       — oriented box (OBB)
    IntersectionResult         — hit/miss result dataclass
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from .targets import Box, Cylinder


@dataclass
class IntersectionResult:
    """Result of a ray-target intersection test (PRD section 18)."""

    hit: bool
    distance: Optional[float] = None
    point: Optional[NDArray[np.float64]] = None
    normal: Optional[NDArray[np.float64]] = None
    surface_id: Optional[str] = None


# ─── Ray-Cylinder Intersection ────────────────────────────────────

def ray_cylinder_intersection(
    ray_origin: NDArray[np.float64],
    ray_direction: NDArray[np.float64],
    cylinder: Cylinder,
) -> IntersectionResult:
    """Analytical ray-infinite-cylinder intersection.

    The cylinder has axis through *cylinder.position* along *cylinder.axis_direction*.
    Only the nearest positive hit is returned.
    """
    O = np.asarray(ray_origin, dtype=np.float64)
    D = np.asarray(ray_direction, dtype=np.float64)
    C = cylinder.position
    V = cylinder.axis_direction
    r = cylinder.radius

    # Vector from cylinder axis point to ray origin
    OC = O - C

    # Decompose: perpendicular and parallel components relative to axis
    D_dot_V = np.dot(D, V)
    OC_dot_V = np.dot(OC, V)

    D_perp = D - D_dot_V * V
    OC_perp = OC - OC_dot_V * V

    # Quadratic: |D_perp|^2 t^2 + 2(D_perp . OC_perp) t + |OC_perp|^2 - r^2 = 0
    a = np.dot(D_perp, D_perp)
    b = 2.0 * np.dot(D_perp, OC_perp)
    c = np.dot(OC_perp, OC_perp) - r * r

    discriminant = b * b - 4.0 * a * c
    if discriminant < 0.0 or a < 1e-30:
        return IntersectionResult(hit=False)

    sqrt_disc = np.sqrt(discriminant)
    t1 = (-b - sqrt_disc) / (2.0 * a)
    t2 = (-b + sqrt_disc) / (2.0 * a)

    # Pick nearest positive
    t = _pick_nearest_positive(t1, t2)
    if t is None:
        return IntersectionResult(hit=False)

    point = O + t * D
    normal = cylinder.surface_normal(point)

    return IntersectionResult(
        hit=True,
        distance=float(t),
        point=point,
        normal=normal,
        surface_id="lateral",
    )


# ─── Ray-Box Intersection ─────────────────────────────────────────

def ray_box_intersection(
    ray_origin: NDArray[np.float64],
    ray_direction: NDArray[np.float64],
    box: Box,
) -> IntersectionResult:
    """Analytical ray-oriented-box (OBB) intersection via slab method.

    Transforms the ray into the box local frame (axis-aligned) and uses the
    standard slab method, then transforms results back to world frame.
    """
    O = np.asarray(ray_origin, dtype=np.float64)
    D = np.asarray(ray_direction, dtype=np.float64)

    R = box.rotation_matrix
    T = box.position
    half = box.half_extents

    # Transform ray into box-local frame
    O_local = R.T @ (O - T)
    D_local = R.T @ D

    result = _ray_aabb_intersection(O_local, D_local, half)
    if not result.hit:
        return result

    # Transform point and normal back to world
    result.point = R @ result.point + T
    result.normal = R @ result.normal
    return result


def _ray_aabb_intersection(
    O: NDArray[np.float64],
    D: NDArray[np.float64],
    half: NDArray[np.float64],
) -> IntersectionResult:
    """Slab-method ray-AABB intersection. Returns nearest hit in local frame."""
    t_min = -np.inf
    t_max = np.inf
    hit_face = 0
    face_sign = 1.0

    for i in range(3):
        if abs(D[i]) < 1e-15:
            if O[i] < -half[i] or O[i] > half[i]:
                return IntersectionResult(hit=False)
            continue

        t1 = (-half[i] - O[i]) / D[i]
        t2 = (half[i] - O[i]) / D[i]

        t_near = min(t1, t2)
        t_far = max(t1, t2)

        if t_near > t_min:
            t_min = t_near
            hit_face = i
            face_sign = -1.0 if t1 == t_near else 1.0

        t_max = min(t_max, t_far)
        if t_min > t_max:
            return IntersectionResult(hit=False)

    t = t_min if t_min > 1e-9 else t_max
    if t < 1e-9:
        return IntersectionResult(hit=False)

    point = O + t * D
    normal = np.zeros(3, dtype=np.float64)
    normal[hit_face] = face_sign
    face_names = ["+x", "-x", "+y", "-y", "+z", "-z"]
    face_idx = hit_face * 2 + (0 if face_sign < 0 else 1)

    return IntersectionResult(
        hit=True,
        distance=float(t),
        point=point,
        normal=normal,
        surface_id=face_names[face_idx],
    )


# ─── helpers ──────────────────────────────────────────────────────

def _pick_nearest_positive(t1: float, t2: float) -> float | None:
    """Return the smallest positive value among t1, t2, or None."""
    candidates = [t for t in (t1, t2) if t > 1e-9]
    return min(candidates) if candidates else None