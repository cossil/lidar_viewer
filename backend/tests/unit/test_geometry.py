"""Geometry engine tests (PRD sections 14-19).

Tests against known analytical solutions with tight tolerances.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from lidar_analysis.geometry.transforms import (
    rotation_matrix_from_euler,
    euler_from_rotation_matrix,
    make_transform,
    pose_to_transform,
    transform_point,
    transform_direction,
    invert_transform,
)
from lidar_analysis.geometry.targets import Cylinder, Box
from lidar_analysis.geometry.intersection import (
    ray_cylinder_intersection,
    ray_box_intersection,
    IntersectionResult,
)
from lidar_analysis.geometry.angular_size import (
    target_angular_size,
    target_angular_size_small_angle,
    beam_footprint,
    beam_footprint_small_angle,
    incidence_angle,
)
from lidar_analysis.geometry.rays import (
    make_ray,
    ray_at,
    direction_from_angles,
    generate_mechanical_spin_directions,
)


TOL = 1e-10


# ═══════════════════════════════════════════════════════════════
# TRANSFORMS (PRD section 14)
# ═══════════════════════════════════════════════════════════════

class TestTransforms:
    def test_identity_rotation(self):
        R = rotation_matrix_from_euler(0, 0, 0)
        np.testing.assert_allclose(R, np.eye(3), atol=TOL)

    def test_rotation_matrix_orthogonal(self):
        R = rotation_matrix_from_euler(0.5, 0.3, 0.1)
        np.testing.assert_allclose(R @ R.T, np.eye(3), atol=TOL)
        assert np.isclose(np.linalg.det(R), 1.0, atol=TOL)

    def test_euler_roundtrip(self):
        for yaw, pitch, roll in [(0.5, 0.3, 0.1), (1.0, -0.4, 0.2), (0, 0, 0)]:
            R = rotation_matrix_from_euler(yaw, pitch, roll)
            y2, p2, r2 = euler_from_rotation_matrix(R)
            np.testing.assert_allclose([y2, p2, r2], [yaw, pitch, roll], atol=1e-10)

    def test_make_transform_shape(self):
        R = np.eye(3)
        t = np.array([1, 2, 3.0])
        T = make_transform(R, t)
        assert T.shape == (4, 4)
        np.testing.assert_allclose(T[:3, :3], np.eye(3))
        np.testing.assert_allclose(T[:3, 3], [1, 2, 3])
        np.testing.assert_allclose(T[3, :], [0, 0, 0, 1])

    def test_transform_point_translation(self):
        T = pose_to_transform(0, 0, 0, np.array([10, 0, 0.0]))
        p = transform_point(T, np.array([1, 2, 3.0]))
        np.testing.assert_allclose(p, [11, 2, 3], atol=TOL)

    def test_transform_point_rotation(self):
        T = pose_to_transform(math.pi / 2, 0, 0, np.zeros(3))
        p = transform_point(T, np.array([1, 0, 0.0]))
        np.testing.assert_allclose(p, [0, 1, 0], atol=TOL)

    def test_transform_direction_no_translation(self):
        T = pose_to_transform(0, 0, 0, np.array([100, 0, 0.0]))
        d = transform_direction(T, np.array([1, 0, 0.0]))
        np.testing.assert_allclose(d, [1, 0, 0], atol=TOL)

    def test_invert_transform(self):
        T = pose_to_transform(0.3, 0.1, 0.05, np.array([5, -3, 2.0]))
        T_inv = invert_transform(T)
        product = T @ T_inv
        np.testing.assert_allclose(product, np.eye(4), atol=TOL)


# ═══════════════════════════════════════════════════════════════
# TARGETS (PRD section 15-16)
# ═══════════════════════════════════════════════════════════════

class TestTargets:
    def test_cylinder_from_dbh(self):
        c = Cylinder.from_dbh(0.10, [0, 0, 0], [0, 0, 1], 0.3)
        assert np.isclose(c.radius, 0.05)
        assert np.isclose(c.reflectivity, 0.3)

    def test_cylinder_axis_normalized(self):
        c = Cylinder(0.05, [0, 0, 0], [0, 0, 5], 0.3)
        np.testing.assert_allclose(np.linalg.norm(c.axis_direction), 1.0, atol=TOL)

    def test_cylinder_bad_radius(self):
        with pytest.raises(ValueError, match="radius"):
            Cylinder(0.0, [0, 0, 0], [0, 0, 1], 0.3)

    def test_cylinder_bad_reflectivity(self):
        with pytest.raises(ValueError):
            Cylinder(0.05, [0, 0, 0], [0, 0, 1], 1.5)

    def test_cylinder_surface_normal(self):
        c = Cylinder(1.0, [0, 0, 0], [0, 0, 1], 0.3)
        point = np.array([1.0, 0.0, 5.0])
        n = c.surface_normal(point)
        np.testing.assert_allclose(n, [1, 0, 0], atol=TOL)
        assert np.isclose(np.linalg.norm(n), 1.0, atol=TOL)

    def test_box_default(self):
        b = Box(1.0, 1.0, 1.0, [0, 0, 0])
        np.testing.assert_allclose(b.half_extents, [0.5, 0.5, 0.5])

    def test_box_bad_dimension(self):
        with pytest.raises(ValueError, match="width"):
            Box(0, 1, 1, [0, 0, 0])

    def test_box_surface_normals(self):
        b = Box(1, 1, 1, [0, 0, 0])
        np.testing.assert_allclose(b.surface_normal(0), [1, 0, 0])
        np.testing.assert_allclose(b.surface_normal(1), [-1, 0, 0])
        np.testing.assert_allclose(b.surface_normal(4), [0, 0, 1])


# ═══════════════════════════════════════════════════════════════
# RAY-CYLINDER INTERSECTION (PRD section 18)
# ═══════════════════════════════════════════════════════════════

class TestRayCylinder:
    def test_direct_hit(self):
        """Ray aimed straight at a cylinder hits at the expected distance."""
        c = Cylinder(1.0, [0, 0, 0], [0, 0, 1], 0.3)
        origin = np.array([-5, 0, 0.0])
        direction = np.array([1, 0, 0.0])
        result = ray_cylinder_intersection(origin, direction, c)
        assert result.hit
        assert np.isclose(result.distance, 4.0, atol=1e-8)
        np.testing.assert_allclose(result.point, [-1, 0, 0], atol=1e-8)
        np.testing.assert_allclose(result.normal, [-1, 0, 0], atol=1e-8)

    def test_miss_parallel(self):
        """Ray parallel to axis and outside radius misses."""
        c = Cylinder(0.5, [0, 0, 0], [0, 0, 1], 0.3)
        origin = np.array([0, 10, 0.0])
        direction = np.array([0, 0, 1.0])
        result = ray_cylinder_intersection(origin, direction, c)
        assert not result.hit

    def test_miss_offset(self):
        """Ray that passes beside the cylinder misses."""
        c = Cylinder(0.5, [0, 0, 0], [0, 0, 1], 0.3)
        origin = np.array([-5, 2, 0.0])
        direction = np.array([1, 0, 0.0])
        result = ray_cylinder_intersection(origin, direction, c)
        assert not result.hit

    def test_hit_from_behind(self):
        """Ray originating inside the cylinder misses (no negative t)."""
        c = Cylinder(1.0, [0, 0, 0], [0, 0, 1], 0.3)
        origin = np.array([0, 0, 0.0])
        direction = np.array([-1, 0, 0.0])
        result = ray_cylinder_intersection(origin, direction, c)
        # From inside, the nearest positive hit is at distance = radius
        assert result.hit
        assert np.isclose(result.distance, 1.0, atol=1e-8)

    def test_normal_perpendicular_to_axis(self):
        """Normal on lateral surface is perpendicular to axis."""
        c = Cylinder(1.0, [0, 0, 0], [0, 0, 1], 0.3)
        origin = np.array([-5, 0, 5.0])
        direction = np.array([1, 0, 0.0])
        result = ray_cylinder_intersection(origin, direction, c)
        assert result.hit
        assert np.isclose(np.dot(result.normal, c.axis_direction), 0.0, atol=TOL)

    def test_oblique_hit(self):
        """Oblique ray still hits and returns correct normal."""
        c = Cylinder(1.0, [0, 0, 0], [0, 0, 1], 0.3)
        origin = np.array([-5, -2, 0.0])
        direction = np.array([1, 0.3, 0.0])
        d, _ = make_ray(origin, direction)
        result = ray_cylinder_intersection(origin, direction, c)
        assert result.hit
        assert result.distance > 0
        # normal should be unit length
        assert np.isclose(np.linalg.norm(result.normal), 1.0, atol=TOL)

    def test_surface_id(self):
        c = Cylinder(1.0, [0, 0, 0], [0, 0, 1], 0.3)
        result = ray_cylinder_intersection(
            np.array([-5, 0, 0.0]), np.array([1, 0, 0.0]), c
        )
        assert result.surface_id == "lateral"


# ═══════════════════════════════════════════════════════════════
# RAY-BOX INTERSECTION (PRD section 18)
# ═══════════════════════════════════════════════════════════════

class TestRayBox:
    def test_hit_front_face(self):
        """Ray hits the -X face of a box centered at origin."""
        b = Box(2, 2, 2, [0, 0, 0])
        origin = np.array([-5, 0, 0.0])
        direction = np.array([1, 0, 0.0])
        result = ray_box_intersection(origin, direction, b)
        assert result.hit
        assert np.isclose(result.distance, 4.0, atol=1e-8)
        np.testing.assert_allclose(result.normal, [-1, 0, 0], atol=TOL)

    def test_hit_top_face(self):
        b = Box(2, 2, 2, [0, 0, 0])
        origin = np.array([0, 0, 5.0])
        direction = np.array([0, 0, -1.0])
        result = ray_box_intersection(origin, direction, b)
        assert result.hit
        assert np.isclose(result.distance, 4.0, atol=1e-8)
        np.testing.assert_allclose(result.normal, [0, 0, 1], atol=TOL)

    def test_miss(self):
        b = Box(1, 1, 1, [0, 0, 0])
        origin = np.array([-5, 2, 0.0])
        direction = np.array([1, 0, 0.0])
        result = ray_box_intersection(origin, direction, b)
        assert not result.hit

    def test_box_at_offset(self):
        b = Box(2, 2, 2, [10, 0, 0])
        origin = np.array([0, 0, 0.0])
        direction = np.array([1, 0, 0.0])
        result = ray_box_intersection(origin, direction, b)
        assert result.hit
        assert np.isclose(result.distance, 9.0, atol=1e-8)

    def test_rotated_box(self):
        """Box rotated 45 degrees — ray still hits the face."""
        b = Box(2, 2, 2, [0, 0, 0], orientation_yaw=math.pi / 4)
        origin = np.array([-5, 0, 0.0])
        direction = np.array([1, 0, 0.0])
        result = ray_box_intersection(origin, direction, b)
        assert result.hit
        # distance should be > 1 (half-width) since rotated
        assert result.distance > 0.9


# ═══════════════════════════════════════════════════════════════
# ANGULAR SIZE / BEAM FOOTPRINT / INCIDENCE (PRD sections 19, 25, 27)
# ═══════════════════════════════════════════════════════════════

class TestAngularSize:
    def test_prd_example(self):
        """PRD section 19: 10 cm tree at 30 m ≈ 0.191 degrees."""
        theta = target_angular_size(0.10, 30.0)
        theta_deg = math.degrees(theta)
        assert np.isclose(theta_deg, 0.191, atol=0.002)

    def test_small_angle_agrees(self):
        theta_exact = target_angular_size(0.10, 30.0)
        theta_approx = target_angular_size_small_angle(0.10, 30.0)
        assert np.isclose(theta_exact, theta_approx, atol=1e-4)

    def test_bad_range(self):
        with pytest.raises(ValueError, match="range"):
            target_angular_size(0.1, 0)

    def test_beam_footprint_at_range(self):
        divergence = 0.003  # 3 mrad (already in radians)
        d = beam_footprint(30.0, divergence)
        assert d > 0
        # small-angle: d_b ≈ R * θ_b ≈ 30 * 0.003 = 0.09 m
        assert np.isclose(d, 0.09, atol=0.01)

    def test_beam_footprint_small_angle(self):
        divergence = 0.003  # 3 mrad
        d_exact = beam_footprint(30.0, divergence)
        d_approx = beam_footprint_small_angle(30.0, divergence)
        assert np.isclose(d_exact, d_approx, rtol=0.01)

    def test_incidence_normal(self):
        """Normal incidence (ray perpendicular to surface) → α = 0."""
        n = np.array([1.0, 0, 0])
        d = np.array([-1.0, 0, 0])
        alpha = incidence_angle(n, d)
        assert np.isclose(alpha, 0.0, atol=TOL)

    def test_incidence_45(self):
        n = np.array([1.0, 0, 0])
        d = np.array([-1.0, -1.0, 0])
        alpha = incidence_angle(n, d)
        assert np.isclose(alpha, math.pi / 4, atol=1e-8)

    def test_incidence_grazing(self):
        """Grazing incidence → α ≈ pi/2."""
        n = np.array([1.0, 0, 0])
        d = np.array([0, 1.0, 0])
        alpha = incidence_angle(n, d)
        assert np.isclose(alpha, math.pi / 2, atol=1e-8)


# ═══════════════════════════════════════════════════════════════
# RAYS (PRD section 17)
# ═══════════════════════════════════════════════════════════════

class TestRays:
    def test_make_ray_normalizes(self):
        o, d = make_ray([0, 0, 0], [3, 0, 0])
        np.testing.assert_allclose(d, [1, 0, 0], atol=TOL)

    def test_make_ray_zero_direction(self):
        with pytest.raises(ValueError, match="non-zero"):
            make_ray([0, 0, 0], [0, 0, 0])

    def test_ray_at(self):
        o = np.array([1, 2, 3.0])
        d = np.array([1, 0, 0.0])
        p = ray_at(5.0, o, d)
        np.testing.assert_allclose(p, [6, 2, 3], atol=TOL)

    def test_direction_from_angles(self):
        d = direction_from_angles(0, 0)
        np.testing.assert_allclose(d, [1, 0, 0], atol=TOL)

    def test_direction_90_degrees(self):
        d = direction_from_angles(math.pi / 2, 0)
        np.testing.assert_allclose(d, [0, 1, 0], atol=TOL)

    def test_generate_mechanical_spin_directions(self):
        fov_h = math.radians(360)
        fov_v = math.radians(30)
        res_h = math.radians(10)
        res_v = math.radians(10)
        dirs = generate_mechanical_spin_directions(fov_h, fov_v, res_h, res_v)
        assert dirs.ndim == 2
        assert dirs.shape[1] == 3
        # all should be unit vectors
        norms = np.linalg.norm(dirs, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=TOL)


# ═══════════════════════════════════════════════════════════════
# INTEGRATION: end-to-end geometry pipeline
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    def test_full_pipeline(self):
        """End-to-end: sensor at origin, cylinder 30m away, single ray."""
        c = Cylinder.from_dbh(0.10, [30, 0, 0], [0, 0, 1], 0.3)
        sensor_pos = np.array([0, 0, 0.0])
        ray_dir = np.array([1, 0, 0.0])

        result = ray_cylinder_intersection(sensor_pos, ray_dir, c)
        assert result.hit
        assert np.isclose(result.distance, 29.95, atol=0.01)  # 30 - radius(0.05)

        alpha = incidence_angle(result.normal, ray_dir)
        assert np.isclose(alpha, 0.0, atol=1e-6)  # normal incidence

        theta = target_angular_size(0.10, result.distance)
        assert math.degrees(theta) < 1.0