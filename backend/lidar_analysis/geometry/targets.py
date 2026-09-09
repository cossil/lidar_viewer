"""Target geometry: Cylinder (ideal tree trunk) and Box.

PRD sections 15-16:
  - Cylinder: radius = DBH / 2, axis along orientation, surface normal at every point.
  - Box: width x depth x height.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from .transforms import rotation_matrix_from_euler, make_transform


@dataclass(frozen=True)
class Cylinder:
    """An ideal cylindrical target (PRD section 15.2).

    The cylinder axis passes through *position* along *axis_direction* (unit vector).
    Only the lateral surface is used for ray intersection (no endcaps).
    """

    radius: float
    position: NDArray[np.float64]
    axis_direction: NDArray[np.float64]
    reflectivity: float

    def __post_init__(self):
        axis = np.asarray(self.axis_direction, dtype=np.float64)
        norm = np.linalg.norm(axis)
        if norm < 1e-12:
            raise ValueError("axis_direction must be non-zero")
        # normalise in-place via object.__setattr__ (frozen)
        object.__setattr__(self, "axis_direction", axis / norm)
        object.__setattr__(self, "position", np.asarray(self.position, dtype=np.float64))
        if self.radius <= 0:
            raise ValueError("radius must be > 0")
        if not (0.0 <= self.reflectivity <= 1.0):
            raise ValueError("reflectivity must be in [0, 1]")

    @classmethod
    def from_dbh(cls, dbh: float, position, axis_direction, reflectivity: float) -> "Cylinder":
        """Create from DBH (m). PRD section 15.2: radius = DBH / 2."""
        return cls(radius=dbh / 2.0, position=position, axis_direction=axis_direction, reflectivity=reflectivity)

    def surface_normal(self, point: NDArray[np.float64]) -> NDArray[np.float64]:
        """Outward normal on the lateral surface at *point*.

        The normal is the component of (point - axis_point) perpendicular to the axis.
        """
        p = np.asarray(point, dtype=np.float64)
        v = p - self.position
        # project onto plane perpendicular to axis
        v_perp = v - np.dot(v, self.axis_direction) * self.axis_direction
        n = np.linalg.norm(v_perp)
        if n < 1e-15:
            # point is on the axis — normal is undefined; pick arbitrary perpendicular
            return _arbitrary_perpendicular(self.axis_direction)
        return v_perp / n


@dataclass(frozen=True)
class Box:
    """An axis-aligned box target (PRD section 15.1).

    Centered at *position*. Orientation is applied as rotation to the box frame.
    """

    width: float
    depth: float
    height: float
    position: NDArray[np.float64]
    orientation_yaw: float = 0.0
    orientation_pitch: float = 0.0
    orientation_roll: float = 0.0
    reflectivity: float = 0.5

    def __post_init__(self):
        for name in ("width", "depth", "height"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be > 0")
        if not (0.0 <= self.reflectivity <= 1.0):
            raise ValueError("reflectivity must be in [0, 1]")
        object.__setattr__(self, "position", np.asarray(self.position, dtype=np.float64))

    @property
    def half_extents(self) -> NDArray[np.float64]:
        return np.array([self.width / 2, self.depth / 2, self.height / 2], dtype=np.float64)

    @property
    def rotation_matrix(self) -> NDArray[np.float64]:
        return rotation_matrix_from_euler(self.orientation_yaw, self.orientation_pitch, self.orientation_roll)

    @property
    def transform(self) -> NDArray[np.float64]:
        return make_transform(self.rotation_matrix, self.position)

    def surface_normal(self, face: int) -> NDArray[np.float64]:
        """Outward normal for the given face index (0-5) in the *box-local* frame.

        Faces: +x=0, -x=1, +y=2, -y=3, +z=4, -z=5.
        """
        normals = np.array(
            [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]],
            dtype=np.float64,
        )
        if not (0 <= face <= 5):
            raise ValueError("face must be 0-5")
        return self.rotation_matrix @ normals[face]


def _arbitrary_perpendicular(axis: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return an arbitrary unit vector perpendicular to *axis*."""
    a = np.asarray(axis, dtype=np.float64)
    # pick the coordinate axis with smallest component to cross
    if abs(a[0]) < 0.9:
        ref = np.array([1.0, 0.0, 0.0])
    else:
        ref = np.array([0.0, 1.0, 0.0])
    v = np.cross(a, ref)
    return v / np.linalg.norm(v)