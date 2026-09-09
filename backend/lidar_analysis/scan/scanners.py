"""Scan engine: generates candidate ray directions from sensor scanning geometry.

PRD section 20: The scan model is a first-class component. Target intersection depends
on the actual angular sampling pattern, NOT point_rate × simulation_time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from numpy.typing import NDArray

from ..geometry.rays import direction_from_angles


@dataclass(frozen=True)
class Channel:
    """A single laser channel on a multi-channel scanner (PRD section 21)."""

    elevation_angle: float
    enabled: bool = True


@dataclass
class ScanPoint:
    """A single candidate measurement ray direction + metadata."""

    horizontal_angle: float
    vertical_angle: float
    channel_index: int
    time: float
    direction: NDArray[np.float64]


class ScanModel(ABC):
    """Base class for all scan models (PRD section 20)."""

    @abstractmethod
    def generate_scan_points(
        self,
        duration: float,
        rng: Optional[np.random.Generator] = None,
    ) -> List[ScanPoint]:
        """Generate candidate measurement points for *duration* seconds.

        Returns a list of ScanPoint with direction vectors in the sensor frame.
        """
        ...


class MechanicalSpinningScanner(ScanModel):
    """Mechanical spinning LiDAR scanner (PRD section 21).

    Rotates around the vertical axis at *rotation_frequency* Hz.
    Each channel fires at *point_rate* total Hz (distributed across all channels).
    Horizontal angular resolution derived from rotation_frequency and point_rate.
    """

    def __init__(
        self,
        horizontal_fov: float,
        vertical_fov: float,
        channels: List[Channel],
        point_rate: float,
        rotation_frequency: float,
        frame_rate: float = 1.0,
        scan_phase: float = 0.0,
    ):
        self.horizontal_fov = horizontal_fov
        self.vertical_fov = vertical_fov
        self.channels = list(channels)
        self.point_rate = point_rate
        self.rotation_frequency = rotation_frequency
        self.frame_rate = frame_rate
        self.scan_phase = scan_phase

        n_enabled = sum(1 for c in self.channels if c.enabled)
        if n_enabled == 0:
            raise ValueError("at least one channel must be enabled")
        if point_rate <= 0:
            raise ValueError("point_rate must be > 0")
        if rotation_frequency <= 0:
            raise ValueError("rotation_frequency must be > 0")

    @classmethod
    def from_sensor_scan(
        cls,
        scan_dict: dict,
        channels: Optional[List[Channel]] = None,
    ) -> "MechanicalSpinningScanner":
        """Create from a sensor scan schema dict."""
        if channels is None:
            raw = scan_dict.get("channels", [])
            channels = [
                Channel(
                    elevation_angle=ch.get("elevation_angle", 0.0),
                    enabled=ch.get("enabled", True),
                )
                for ch in raw
            ]
            if not channels:
                channels = [Channel(elevation_angle=0.0)]

        def _val(d, key, default):
            v = d.get(key, {})
            if isinstance(v, dict):
                return v.get("value", default)
            return v if v is not None else default

        return cls(
            horizontal_fov=_val(scan_dict, "horizontal_fov", 2 * np.pi),
            vertical_fov=_val(scan_dict, "vertical_fov", 0.0),
            channels=channels,
            point_rate=_val(scan_dict, "point_rate", 300000),
            rotation_frequency=_val(scan_dict, "rotation_frequency", 10),
            frame_rate=_val(scan_dict, "frame_rate", 10),
            scan_phase=scan_dict.get("scan_phase", 0.0),
        )

    def generate_scan_points(
        self,
        duration: float,
        rng: Optional[np.random.Generator] = None,
    ) -> List[ScanPoint]:
        """Generate scan points for a mechanical spinning scanner.

        Each rotation: all enabled channels fire at their elevation angles,
        sweeping through horizontal angles at the rotation rate.
        """
        if duration <= 0:
            raise ValueError("duration must be > 0")

        points: List[ScanPoint] = []
        enabled_channels = [c for c in self.channels if c.enabled]
        n_channels = len(enabled_channels)

        # horizontal angular resolution: points per rotation = point_rate / rotation_frequency
        points_per_rotation = self.point_rate / self.rotation_frequency
        horizontal_step = 2 * np.pi / points_per_rotation if points_per_rotation > 0 else 0

        total_rotations = duration * self.rotation_frequency
        total_points = int(self.point_rate * duration)

        for i in range(total_points):
            t = i / self.point_rate
            rotation_fraction = (t * self.rotation_frequency) % 1.0
            h_angle = rotation_fraction * 2 * np.pi + self.scan_phase

            channel_idx = i % n_channels
            v_angle = enabled_channels[channel_idx].elevation_angle

            direction = direction_from_angles(h_angle, v_angle)
            points.append(ScanPoint(
                horizontal_angle=h_angle,
                vertical_angle=v_angle,
                channel_index=channel_idx,
                time=t,
                direction=direction,
            ))

        return points


class StructuredRasterScanner(ScanModel):
    """Structured/raster scan LiDAR (PRD section 22).

    Scans in a raster pattern: sweeps horizontally line by line.
    """

    def __init__(
        self,
        horizontal_fov: float,
        vertical_fov: float,
        horizontal_step: float,
        vertical_step: float,
        frame_rate: float = 1.0,
        scan_phase: float = 0.0,
    ):
        self.horizontal_fov = horizontal_fov
        self.vertical_fov = vertical_fov
        self.horizontal_step = horizontal_step
        self.vertical_step = vertical_step
        self.frame_rate = frame_rate
        self.scan_phase = scan_phase

        if horizontal_step <= 0:
            raise ValueError("horizontal_step must be > 0")
        if vertical_step <= 0:
            raise ValueError("vertical_step must be > 0")

    @classmethod
    def from_sensor_scan(cls, scan_dict: dict) -> "StructuredRasterScanner":
        def _val(d, key, default):
            v = d.get(key, {})
            if isinstance(v, dict):
                return v.get("value", default)
            return v if v is not None else default

        return cls(
            horizontal_fov=_val(scan_dict, "horizontal_fov", np.pi / 4),
            vertical_fov=_val(scan_dict, "vertical_fov", np.pi / 8),
            horizontal_step=_val(scan_dict, "horizontal_angular_step", np.radians(0.1)),
            vertical_step=_val(scan_dict, "vertical_angular_step", np.radians(0.1)),
            frame_rate=_val(scan_dict, "frame_rate", 10),
            scan_phase=scan_dict.get("scan_phase", 0.0),
        )

    def generate_scan_points(
        self,
        duration: float,
        rng: Optional[np.random.Generator] = None,
    ) -> List[ScanPoint]:
        if duration <= 0:
            raise ValueError("duration must be > 0")

        points: List[ScanPoint] = []
        h_angles = np.arange(
            -self.horizontal_fov / 2,
            self.horizontal_fov / 2,
            self.horizontal_step,
        )
        v_angles = np.arange(
            -self.vertical_fov / 2,
            self.vertical_fov / 2,
            self.vertical_step,
        )

        # one frame = all v_angles x h_angles
        points_per_frame = len(h_angles) * len(v_angles)
        if points_per_frame == 0:
            return points

        frames = max(1, int(duration * self.frame_rate))
        t_per_point = 1.0 / (points_per_frame * self.frame_rate) if points_per_frame > 0 else 0

        idx = 0
        for frame in range(frames):
            frame_start = frame / self.frame_rate
            for vi, v in enumerate(v_angles):
                for hi, h in enumerate(h_angles):
                    t = frame_start + idx * t_per_point
                    if t >= duration:
                        return points
                    direction = direction_from_angles(h + self.scan_phase, v)
                    points.append(ScanPoint(
                        horizontal_angle=h,
                        vertical_angle=v,
                        channel_index=vi,
                        time=t,
                        direction=direction,
                    ))
                    idx += 1
            idx = 0

        return points


class NonRepetitiveScanner(ScanModel):
    """Non-repetitive scanner (PRD section 23).

    MVP: uses an analytical coverage model. Non-repetitive sensors
    progressively cover their FOV as integration time increases.
    """

    def __init__(
        self,
        horizontal_fov: float,
        vertical_fov: float,
        point_rate: float,
        integration_time: float = 1.0,
    ):
        self.horizontal_fov = horizontal_fov
        self.vertical_fov = vertical_fov
        self.point_rate = point_rate
        self.integration_time = integration_time

        if point_rate <= 0:
            raise ValueError("point_rate must be > 0")

    def generate_scan_points(
        self,
        duration: float,
        rng: Optional[np.random.Generator] = None,
    ) -> List[ScanPoint]:
        """MVP: generate uniformly random directions within the FOV.

        Non-repetitive sensors progressively cover their FOV over time.
        """
        if duration <= 0:
            raise ValueError("duration must be > 0")
        if rng is None:
            rng = np.random.default_rng()

        n_points = int(self.point_rate * duration)
        points: List[ScanPoint] = []

        h_angles = rng.uniform(-self.horizontal_fov / 2, self.horizontal_fov / 2, n_points)
        v_angles = rng.uniform(-self.vertical_fov / 2, self.vertical_fov / 2, n_points)

        for i in range(n_points):
            t = i / self.point_rate
            direction = direction_from_angles(h_angles[i], v_angles[i])
            points.append(ScanPoint(
                horizontal_angle=h_angles[i],
                vertical_angle=v_angles[i],
                channel_index=0,
                time=t,
                direction=direction,
            ))

        return points