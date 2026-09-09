"""Coordinate transforms: Euler angles to/from rotation matrix, 4x4 homogeneous poses.

PRD section 14: right-handed Cartesian; LiDAR pose as T_L = [[R,p],[0,1]].
Internally rotations use matrices, not repeated Euler composition.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def rotation_matrix_from_euler(yaw: float, pitch: float, roll: float) -> NDArray[np.float64]:
    """Build a 3x3 rotation matrix from Tait-Bryan ZYX Euler angles (radians).

    Convention (PRD section 14):
      - yaw   = rotation about Z
      - pitch = rotation about Y (clamped to +/- pi/2 by caller)
      - roll  = rotation about X

    R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
    """
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cr, sr = np.cos(roll), np.sin(roll)

    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ],
        dtype=np.float64,
    )


def euler_from_rotation_matrix(R: NDArray[np.float64]) -> tuple[float, float, float]:
    """Extract (yaw, pitch, roll) from a rotation matrix (ZYX convention).

    Inverse of :func:`rotation_matrix_from_euler`.
    """
    pitch = np.arcsin(np.clip(-R[2, 0], -1.0, 1.0))
    if np.abs(np.cos(pitch)) < 1e-12:
        # gimbal lock
        yaw = np.arctan2(R[1, 2], R[0, 2])
        roll = 0.0
    else:
        yaw = np.arctan2(R[1, 0], R[0, 0])
        roll = np.arctan2(R[2, 1], R[2, 2])
    return float(yaw), float(pitch), float(roll)


def make_transform(R: NDArray[np.float64], t: NDArray[np.float64]) -> NDArray[np.float64]:
    """Build a 4x4 homogeneous transform from 3x3 rotation and translation.

    Returns:
        T = [[R, t],
             [0, 1]]
    """
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def pose_to_transform(yaw: float, pitch: float, roll: float, position: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert Euler angles + position to a 4x4 homogeneous transform."""
    R = rotation_matrix_from_euler(yaw, pitch, roll)
    return make_transform(R, np.asarray(position, dtype=np.float64))


def transform_point(T: NDArray[np.float64], p: NDArray[np.float64]) -> NDArray[np.float64]:
    """Apply a 4x4 transform to a 3D point (homogeneous coordinates)."""
    p_h = np.append(np.asarray(p, dtype=np.float64), 1.0)
    return (T @ p_h)[:3]


def transform_direction(T: NDArray[np.float64], d: NDArray[np.float64]) -> NDArray[np.float64]:
    """Apply the rotation part of a 4x4 transform to a direction vector (no translation)."""
    return T[:3, :3] @ np.asarray(d, dtype=np.float64)


def invert_transform(T: NDArray[np.float64]) -> NDArray[np.float64]:
    """Invert a rigid-body 4x4 homogeneous transform (R^T, -R^T @ t)."""
    R = T[:3, :3]
    t = T[:3, 3]
    T_inv = np.eye(4, dtype=np.float64)
    T_inv[:3, :3] = R.T
    T_inv[:3, 3] = -R.T @ t
    return T_inv