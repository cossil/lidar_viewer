"""Single-trial simulation engine (PRD section 35).

Pipeline per candidate ray:
  Candidate Ray → Target Intersection? → True Range → Surface Normal →
  Incidence Angle → Beam/Target Overlap → Return Strength →
  Detection Probability → Bernoulli Trial → Measurement Error → Synthetic Point
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from ..geometry.intersection import IntersectionResult, ray_cylinder_intersection, ray_box_intersection
from ..geometry.angular_size import incidence_angle, beam_footprint, target_angular_size
from ..geometry.targets import Cylinder, Box
from ..physics.beam import beam_target_overlap, return_strength as compute_strength
from ..physics.detection import DetectionModel, DetectionResult
from ..physics.measurement import MeasurementModel, MeasurementSample
from ..scan.scanners import ScanPoint


@dataclass
class HitRecord:
    """Record for a single candidate ray that hit the target."""

    scan_point: ScanPoint
    intersection: IntersectionResult
    incidence_angle: float
    overlap: float
    strength: float
    detection_result: DetectionResult
    detected: bool
    measurement: Optional[MeasurementSample] = None


@dataclass
class TrialResult:
    """Result of a single simulation trial."""

    total_rays: int
    hits: int
    detections: int
    hit_records: List[HitRecord] = field(default_factory=list)
    detected_records: List[HitRecord] = field(default_factory=list)

    @property
    def expected_returns(self) -> float:
        """Expected target returns = sum of detection probabilities."""
        return sum(r.detection_result.probability or 0 for r in self.hit_records)

    @property
    def detection_probability(self) -> float:
        """Fraction of hitting rays that were detected."""
        if self.hits == 0:
            return 0.0
        return self.detections / self.hits


class SingleTrialEngine:
    """Runs one simulation trial: scan → intersect → detect → measure."""

    def __init__(
        self,
        target: Cylinder | Box,
        detection_model: DetectionModel,
        measurement_model: MeasurementModel,
        beam_divergence: float,
        rng: np.random.Generator,
    ):
        self.target = target
        self.detection_model = detection_model
        self.measurement_model = measurement_model
        self.beam_divergence = beam_divergence
        self.rng = rng

    def run(
        self,
        scan_points: List[ScanPoint],
        sensor_position: np.ndarray,
    ) -> TrialResult:
        """Execute one trial: process all scan points against the target."""
        hit_records: List[HitRecord] = []
        detected_records: List[HitRecord] = []
        total_hits = 0

        reflectivity = self.target.reflectivity

        for sp in scan_points:
            # 1. Ray-target intersection
            if isinstance(self.target, Cylinder):
                intersection = ray_cylinder_intersection(
                    sensor_position, sp.direction, self.target
                )
            else:
                intersection = ray_box_intersection(
                    sensor_position, sp.direction, self.target
                )

            if not intersection.hit:
                continue

            total_hits += 1
            true_range = intersection.distance

            # 2. Incidence angle
            alpha = incidence_angle(intersection.normal, sp.direction)

            # 3. Beam footprint at this range
            beam_d = beam_footprint(true_range, self.beam_divergence)

            # 4. Beam/target overlap
            target_d = getattr(self.target, "diameter", None)
            if target_d is None:
                target_d = getattr(self.target, "width", 0.1)
            G = beam_target_overlap(target_d, beam_d)

            # 5. Effective area and return strength
            if isinstance(self.target, Cylinder):
                from ..physics.beam import effective_illuminated_area_cylinder
                A_eff = effective_illuminated_area_cylinder(beam_d, target_d, alpha)
            else:
                A_eff = min(beam_d ** 2, target_d ** 2)

            S = compute_strength(reflectivity, A_eff, alpha, true_range)

            # 6. Detection probability
            det_result = self.detection_model.compute_detection_probability(
                range_to_target=true_range,
                reflectivity=reflectivity,
                incidence_angle=alpha,
                beam_target_overlap=G,
                return_strength=S,
            )

            # 7. Bernoulli trial
            p_d = det_result.probability or 0.0
            detected = bool(self.rng.random() < p_d)

            # 8. Measurement error (only if detected)
            measurement = None
            if detected:
                measurement = self.measurement_model.apply(
                    true_range=true_range,
                    true_angle_h=sp.horizontal_angle,
                    true_angle_v=sp.vertical_angle,
                    rng=self.rng,
                )

            record = HitRecord(
                scan_point=sp,
                intersection=intersection,
                incidence_angle=alpha,
                overlap=G,
                strength=S,
                detection_result=det_result,
                detected=detected,
                measurement=measurement,
            )
            hit_records.append(record)
            if detected:
                detected_records.append(record)

        return TrialResult(
            total_rays=len(scan_points),
            hits=total_hits,
            detections=len(detected_records),
            hit_records=hit_records,
            detected_records=detected_records,
        )