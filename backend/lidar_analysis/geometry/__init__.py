"""Geometry engine: coordinate transforms, target models, ray intersection, angular size.

PRD sections 14-19.
"""

from .angular_size import (
    beam_footprint,
    beam_footprint_small_angle,
    incidence_angle,
    target_angular_size,
    target_angular_size_small_angle,
)
from .intersection import IntersectionResult, ray_box_intersection, ray_cylinder_intersection
from .rays import direction_from_angles, generate_mechanical_spin_directions, make_ray, ray_at
from .targets import Box, Cylinder
from .transforms import (
    euler_from_rotation_matrix,
    invert_transform,
    make_transform,
    pose_to_transform,
    rotation_matrix_from_euler,
    transform_direction,
    transform_point,
)

__all__ = [
    # transforms
    "rotation_matrix_from_euler",
    "euler_from_rotation_matrix",
    "make_transform",
    "pose_to_transform",
    "transform_point",
    "transform_direction",
    "invert_transform",
    # targets
    "Cylinder",
    "Box",
    # intersection
    "IntersectionResult",
    "ray_cylinder_intersection",
    "ray_box_intersection",
    # rays
    "make_ray",
    "ray_at",
    "direction_from_angles",
    "generate_mechanical_spin_directions",
    # angular size
    "target_angular_size",
    "target_angular_size_small_angle",
    "beam_footprint",
    "beam_footprint_small_angle",
    "incidence_angle",
]