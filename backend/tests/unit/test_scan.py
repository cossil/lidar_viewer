"""Scan engine tests (PRD sections 20-24).

Tests:
  - Mechanical spinning: direction count, angular coverage, rotation pattern
  - Structured raster: raster ordering, frame generation
  - Non-repetitive: random coverage, FOV bounds
  - Scan duration independence from MC trials
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from lidar_analysis.scan.scanners import (
    Channel,
    MechanicalSpinningScanner,
    NonRepetitiveScanner,
    ScanPoint,
    StructuredRasterScanner,
)


class TestMechanicalSpinningScanner:
    def test_basic_generation(self):
        """Mechanical spinning scanner generates expected number of points."""
        scanner = MechanicalSpinningScanner(
            horizontal_fov=2 * math.pi,
            vertical_fov=math.radians(30),
            channels=[Channel(elevation_angle=0.0)],
            point_rate=1000,
            rotation_frequency=10,
        )
        points = scanner.generate_scan_points(duration=0.1)
        # 1000 pts/s * 0.1s = 100 points
        assert len(points) == 100

    def test_multi_channel(self):
        """Multi-channel scanner distributes points across channels."""
        channels = [
            Channel(elevation_angle=math.radians(-15)),
            Channel(elevation_angle=math.radians(0)),
            Channel(elevation_angle=math.radians(15)),
        ]
        scanner = MechanicalSpinningScanner(
            horizontal_fov=2 * math.pi,
            vertical_fov=math.radians(30),
            channels=channels,
            point_rate=3000,
            rotation_frequency=10,
        )
        points = scanner.generate_scan_points(duration=0.01)
        # should cycle through 3 channels
        channel_indices = [p.channel_index for p in points]
        assert set(channel_indices) == {0, 1, 2}

    def test_directions_are_unit_vectors(self):
        scanner = MechanicalSpinningScanner(
            horizontal_fov=2 * math.pi,
            vertical_fov=math.radians(30),
            channels=[Channel(elevation_angle=0.0)],
            point_rate=100,
            rotation_frequency=10,
        )
        points = scanner.generate_scan_points(duration=0.05)
        for p in points:
            norm = np.linalg.norm(p.direction)
            assert np.isclose(norm, 1.0, atol=1e-10)

    def test_horizontal_sweep(self):
        """Horizontal angles should sweep from 0 toward 2pi."""
        scanner = MechanicalSpinningScanner(
            horizontal_fov=2 * math.pi,
            vertical_fov=math.radians(30),
            channels=[Channel(elevation_angle=0.0)],
            point_rate=100,
            rotation_frequency=10,
            scan_phase=0.0,
        )
        points = scanner.generate_scan_points(duration=0.1)
        h_angles = [p.horizontal_angle for p in points]
        # first point near 0, last near 2pi
        assert h_angles[0] < 0.1
        assert h_angles[-1] > 5.0

    def test_duration_must_be_positive(self):
        scanner = MechanicalSpinningScanner(
            horizontal_fov=2 * math.pi,
            vertical_fov=math.radians(30),
            channels=[Channel(elevation_angle=0.0)],
            point_rate=100,
            rotation_frequency=10,
        )
        with pytest.raises(ValueError, match="duration"):
            scanner.generate_scan_points(duration=0)

    def test_no_channels_raises(self):
        with pytest.raises(ValueError, match="at least one channel"):
            MechanicalSpinningScanner(
                horizontal_fov=2 * math.pi,
                vertical_fov=math.radians(30),
                channels=[Channel(elevation_angle=0.0, enabled=False)],
                point_rate=100,
                rotation_frequency=10,
            )

    def test_from_sensor_scan(self):
        """Create from sensor scan schema dict."""
        scan_dict = {
            "type": "mechanical_spinning",
            "point_rate": {"value": 300000, "unit": "Hz"},
            "rotation_frequency": {"value": 10, "unit": "Hz"},
            "frame_rate": {"value": 10, "unit": "Hz"},
            "channels": [
                {"elevation_angle": -0.2618, "enabled": True},
                {"elevation_angle": 0.0, "enabled": True},
                {"elevation_angle": 0.2618, "enabled": True},
            ],
        }
        scanner = MechanicalSpinningScanner.from_sensor_scan(scan_dict)
        assert scanner.point_rate == 300000
        assert len(scanner.channels) == 3


class TestStructuredRasterScanner:
    def test_basic_generation(self):
        scanner = StructuredRasterScanner(
            horizontal_fov=math.radians(40),
            vertical_fov=math.radians(20),
            horizontal_step=math.radians(10),
            vertical_step=math.radians(10),
            frame_rate=10,
        )
        points = scanner.generate_scan_points(duration=0.1)
        assert len(points) > 0

    def test_raster_ordering(self):
        """Within a frame, raster should sweep horizontal first, then vertical."""
        scanner = StructuredRasterScanner(
            horizontal_fov=math.radians(30),
            vertical_fov=math.radians(30),
            horizontal_step=math.radians(10),
            vertical_step=math.radians(10),
            frame_rate=1,
        )
        points = scanner.generate_scan_points(duration=1.0)
        # within first frame: first row should have same vertical angle
        # 3 h_angles × 3 v_angles = 9 points per frame; first 3 are row 0
        first_v = points[0].vertical_angle
        for p in points[1:3]:
            assert np.isclose(p.vertical_angle, first_v, atol=1e-10)
        # next row should have different vertical angle
        assert not np.isclose(points[3].vertical_angle, first_v, atol=1e-6)

    def test_directions_are_unit_vectors(self):
        scanner = StructuredRasterScanner(
            horizontal_fov=math.radians(40),
            vertical_fov=math.radians(20),
            horizontal_step=math.radians(10),
            vertical_step=math.radians(10),
        )
        points = scanner.generate_scan_points(duration=0.05)
        for p in points:
            assert np.isclose(np.linalg.norm(p.direction), 1.0, atol=1e-10)

    def test_from_sensor_scan(self):
        scan_dict = {
            "type": "structured_raster",
            "horizontal_fov": {"value": 0.7854, "unit": "rad"},
            "vertical_fov": {"value": 0.3927, "unit": "rad"},
            "horizontal_angular_step": {"value": 0.00175, "unit": "rad"},
            "vertical_angular_step": {"value": 0.00175, "unit": "rad"},
            "frame_rate": {"value": 10, "unit": "Hz"},
        }
        scanner = StructuredRasterScanner.from_sensor_scan(scan_dict)
        assert np.isclose(scanner.horizontal_fov, 0.7854, atol=1e-3)


class TestNonRepetitiveScanner:
    def test_generates_points(self):
        scanner = NonRepetitiveScanner(
            horizontal_fov=math.radians(60),
            vertical_fov=math.radians(30),
            point_rate=1000,
        )
        rng = np.random.default_rng(42)
        points = scanner.generate_scan_points(duration=0.1, rng=rng)
        assert len(points) == 100

    def test_directions_within_fov(self):
        scanner = NonRepetitiveScanner(
            horizontal_fov=math.radians(60),
            vertical_fov=math.radians(30),
            point_rate=100,
        )
        rng = np.random.default_rng(42)
        points = scanner.generate_scan_points(duration=1.0, rng=rng)
        for p in points:
            assert abs(p.horizontal_angle) <= scanner.horizontal_fov / 2 + 1e-10
            assert abs(p.vertical_angle) <= scanner.vertical_fov / 2 + 1e-10

    def test_deterministic_with_seed(self):
        scanner = NonRepetitiveScanner(
            horizontal_fov=math.radians(60),
            vertical_fov=math.radians(30),
            point_rate=100,
        )
        rng1 = np.random.default_rng(123)
        rng2 = np.random.default_rng(123)
        pts1 = scanner.generate_scan_points(duration=0.1, rng=rng1)
        pts2 = scanner.generate_scan_points(duration=0.1, rng=rng2)
        for a, b in zip(pts1, pts2):
            np.testing.assert_allclose(a.direction, b.direction)


class TestScanDurationIndependence:
    def test_duration_independent_from_mc(self):
        """PRD section 24: scan duration independent from MC trial count.

        A 1-second scan should have the same angular pattern regardless of
        how many Monte Carlo trials are run.
        """
        scanner = MechanicalSpinningScanner(
            horizontal_fov=2 * math.pi,
            vertical_fov=math.radians(30),
            channels=[Channel(elevation_angle=0.0)],
            point_rate=1000,
            rotation_frequency=10,
        )
        # 1 second scan = 1000 points
        points_1s = scanner.generate_scan_points(duration=1.0)
        assert len(points_1s) == 1000
        # 0.5 second scan = 500 points
        points_half = scanner.generate_scan_points(duration=0.5)
        assert len(points_half) == 500
        # The first 500 points of the 1s scan should match the 0.5s scan
        for a, b in zip(points_1s[:500], points_half):
            np.testing.assert_allclose(a.direction, b.direction)