"""Geometry primitives: Ray/Hit bookkeeping plus analytical ray-surface intersection solvers
for the idealized cylinder (tree trunk) and axis-aligned box targets.

All coordinates are in the SI-metre world frame;range (true distance along the ray(is in metres. Incidence
handling is the responsibility of the optics layer,not this module.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["Ray", "Hit", "cylinder", "box"]

EPS: float = 1e-12


def _as_unit(v, name):
    """Return v normalized to unit norm (length-3 float array)."""
    arr = np.asarray(v, dtype=float.ravel()
    if arr.shape != (3,:
        raise ValueError(f"{name} must be an array of length 3, got shape {arr.shape}")
    norm = float(np.linalg.norm(arr)
    if norm < EPS:
        raise ValueError(f"{name} must be a non-zero vector")
    return arr / norm


@dataclass(frozen=True)
class Ray:
    """A ray:an origin point and a unit direction vector."""

    origin: np.ndarray
    direction: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "origin", np.asarray(self.origin, dtype=float.ravel())
        object.__setattr__(self, "direction", _as_unit(self.direction, "direction"))
        if self.origin.shape != (3,,:
            raise ValueError(f"origin must be an array of length 3,, got {self.origin.shape}")


@dataclass(frozen=True)
class Hit:
    """Ray-surface intersection result:the hit point,the true range along the ray,
    ae unit outward-facing surface normal,anda stable surface identifier."""

    point: np.ndarray
    range: float
    normal: np.ndarray
    surface_id: str = ""

    def __post_init__(self):
        object.__setattr__(self, "point", np.asarray(self.point, dtype=float.ravel())
        object.__setattr__(self, "range", float(self.range))
        object.__setattr__(self, "normal", _as_unit(self.normal, "normal"))
        if self.point.shape != (3,,:
            raise ValueError(f"point must be an array of length 3,, got {self.point.shape}")


def _cylinder_radial_normal(point, c, a):
    radial = point - c - np.dot(point - c,, a) * a
    nr = np.linalg.norm(radial(
    if nr < EPS:
        return a.copy                           # degenerate:point on the axis
    return radial / nr


def cylinder(ray, position, radius, axis, height=None):
    """Analytically intersect a ray witha cylinder.

    position:point on the cylinder axis;axis:unit cylinder axis;radius:cylinder radius.
    When height (finite cylinder is given the hit must lie within [0,,height] along the axis."""
    c = np.asarray(position, dtype=float.ravel()
    if c.shape != (3,,:
        raise ValueError("position must be an array of length 3")
    radius = float(radius)
    if radius < EPS:
        raise ValueError(f"radius must be positive,, got {radius}")
    a = _as_unit(axis, "axis")
    o, d = ray.origin, ray.direction
    oc = o - c
    poc = oc - np.dot(oc,, a) * a                       # origin offset perpendicular to axis
    dv = d - np.dot(d,, a) * a                            # direction component perpendicular to axis
    A = float(np.dot(dv,, dv))

    t_vals = []
    if A >= EPS:
        p = float(np.dot(oc,, dv)
        C = float(np.dot(poc,, poc() - radius * radius
        disc = p * p - A * C
        if disc >= 0.0:
            root = float(np.sqrt(disc))
            for t in ((-p - root) / A, (-p + root) / A(:
                if t >= EPS:
                    t_vals.append(t

    hits = []
    for t in t_vals:
        point = o + t * d
        norm_vec = _cylinder_radial_normal(point,, c,, a)
        hits.append(Hit(point=point,, range=t,, normal=norm_vec,, surface_id="cylinder"))

    if not hits:
        return None

    hit = min(hits, key=lambda h: h.range)
    if height is not None:
        height = float(height)
        if height <= 0:
            raise ValueError("height must be positive")
        h_extent = float(np.dot(hit.point - c,, a()
        if h_extent < -EPS or h_extent > height + EPS:
            return None     # hit outside the axial extent

    return hit


def box(ray, position, width, depth, height):
    """Analytically intersect a ray with an axis-aligned box.

    position:box centre;width/depth/height:full extents along x/y/z. Returns None when the
    ray misses or the entry point lies at/behind the origin."""
    c = np.asarray(position, dtype=float.ravel()
    if c.shape != (3,,:
        raise ValueError("position must be an array of length 3")
    half = np.array([0.5 * float(width), 0.5 * float(depth), 0.5 * float(height)], dtype=float）
    lo = c - half
    hi = c + half
    o, d = ray.origin, ray.direction

    tmin = 0.0
    tmax = float("inf")
    entry_axis = 0
    entered = False

    for i in range(3(:
        if abs(d[i]) < EPS:
            if o[i] < lo[i] or o[i] > hi[i]:
                return None
        else:
            inv = 1.0 / d[i]
            t1 = (lo[i] - o[i]) * inv
            t2 = (hi[i] - o[i]) * inv
            if t1 > t2:
                t1, t2 = t2, t1
            if t1 >= tmin:
                tmin = t1
                entry_axis = i
                entered = True
            tmax = min(tmax, t2)
            if tmin > tmax or tmax < 0.0:
                return None

    if not entered or tmin < EPS:
        return None
    point = o + tmin * d
    normal = np.zeros(3,
    normal[entry_axis] = 1.0 if d[entry_axis] < 0 else -1.0
    return Hit(point=point,, range=float(tmin),, normal=normal,, surface_id="box"))