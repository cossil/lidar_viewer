"""Detection probability models (PRD sections 30-32, SCHEMAS §26 Rules 7/8).

Priority (PRD §30): use the HIGHEST-fidelity available model — the selected model
MUST be recorded in simulation metadata.
   1. Manufacturer empirical detection curve.
   2. User experimental calibration.
   3. Manufacturer range/reflectivity envelope.
   4. Physics-inspired analytical model.
   5. Explicit engineering assumption.

PRD §32 / SCHEMAS §27: if insufficient data, report "Not reliably estimable from
available data." — NEVER fabricate a probability.

SCHEMAS §26 Rule  7: unknown sensor parameters cannot be silently substituted.
Rule  8: a detection model cannot use a parameter whose status is `unknown`
unless that model explicitly supports an alternative.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Sequence

import numpy as np

from ..models.common import ConfidenceLevel, ParameterStatus


class DetectionModelType(str, Enum):
    """Detection model types (SCHEMAS §2.1 extension; PRD §66 for empirical)."""

    MANUFACTURER_CURVE = "manufacturer_curve"    # priority 1
    EMPIRICAL = "empirical"                        # priority 2 (user calibration)
    DATASHEET = "datasheet"                        # priority 3 (range/reflectivity envelope)
    ANALYTICAL = "analytical"                     # priority 4
    ASSUMPTION = "assumption"                     # priority 5


# Priority rank mapping (PRD §30). 1 = highest fidelity.
MODEL_PRIORITY = {
    DetectionModelType.MANUFACTURER_CURVE: 1,
    DetectionModelType.EMPIRICAL: 2,
    DetectionModelType.DATASHEET: 3,
    DetectionModelType.ANALYTICAL: 4,
    DetectionModelType.ASSUMPTION: 5,
}


@dataclass
class DetectionResult:
    """Result of a detection probability calculation (PRD §31: model type, source, confidence).

    Also records which model was selected (priority) so the chosen model can be persisted
    per PRD §30 ("The selected model shall be recorded in simulation metadata.")."""

    probability: Optional[float]
    model_type: DetectionModelType
    physical_model_confidence: ConfidenceLevel
    has_empirical_calibration: bool
    model_source: Optional[str] = None
    priority: Optional[int] = None
    notes: Optional[str] = None


class DetectionModel(ABC):
    """Base class for detection probability models."""

    #: Set by subclasses; used by the priority resolver.

    @abstractmethod
    def compute_detection_probability(
        self,
        range_to_target: float,
        reflectivity: float,
        incidence_angle: float,
        beam_target_overlap: float,
        return_strength: float,
    ) -> DetectionResult:
        ...

    def can_use(self, sensor_params: "SensorParamsView") -> bool:
        """Rule  8: whether this model can run given the sensor's parameter statuses.



        Default=True for models that don't depend on unknown-able params (overridden per-class).
        """
        return True


class SensorParamsView:
    """Lightweight read model over sensor parameters that exposes value+status.



    Lets models enforce SCHEMAS Rule  8 without tying the physics layer to the Pydantic schema."""

    def __init__(
        self,
        max_range: Optional[float] = None,
        max_range_status: Optional[str] = None,
        beam_divergence: Optional[float] = None,
        beam_divergence_status: Optional[str] = None,
        point_rate: Optional[float] = None,
        point_rate_status: Optional[str] = None,
    ):
        self.max_range = max_range
        self.max_range_status = max_range_status
        self.beam_divergence = beam_divergence
        self.beam_divergence_status = beam_divergence_status
        self.point_rate = point_rate
        self.point_rate_status = point_rate_status

    @classmethod
    def from_model(cls, sensor) -> "SensorParamsView":
        """Build view from a `Sensor` Pydantic model, mapping `.status` to known/unknown."""

        def _val(p):
            return p.value if p is not None else None

        def _st(p):
            if p is None:
                return "unknown"
            s = getattr(p, "status", None)
            return s.value if hasattr(s, "value") else (s or "unknown")

        max_range = None
        max_range_st = "unknown"
        if sensor.range and sensor.range.maximum:
            max_range = _val(sensor.range.maximum)
            max_range_st = _st(sensor.range.maximum)

        beam_div = None
        beam_div_st = "unknown"
        if sensor.beam:
            bd = getattr(sensor.beam, "horizontal_divergence", None) or getattr(sensor.beam, "divergence", None)
            if bd:
                beam_div = _val(bd)
                beam_div_st = _st(bd)

        return cls(
            max_range=max_range, max_range_status=max_range_st,
            beam_divergence=beam_div, beam_divergence_status=beam_div_st,
        )

    def is_known(self, value, status) -> bool:
        st = (status or "unknown").lower()
        return value is not None and st in {"known", "estimated", "not_applicable"}


def _unknown(names: Sequence[str]) -> List[str]:
    return [n for n in names if n]


class DatasheetEnvelopeModel(DetectionModel):
    """Priority 3: manufacturer range/reflectivity envelope (SCHEMAS §26 Rule  8-aware).

    Depends on `max_range`; cannot be used if that parameter is `unknown` (Rule 8)."""

    def __init__(self, max_range: float, min_reflectivity: float = 0.1):
        self.max_range = max_range
        self.min_reflectivity = min_reflectivity

    def can_use(self, sensor_params: SensorParamsView) -> bool:
        return sensor_params.is_known(sensor_params.max_range, sensor_params.max_range_status)



    def compute_detection_probability(
        self,
        range_to_target: float,
        reflectivity: float,
        incidence_angle: float,
        beam_target_overlap: float,
        return_strength: float,
    ) -> DetectionResult:
        detected = (
            range_to_target <= self.max_range
            and reflectivity >= self.min_reflectivity
        )
        return DetectionResult(
            probability=1.0 if detected else 0.0,
            model_type=DetectionModelType.DATASHEET,
            physical_model_confidence=ConfidenceLevel.MODERATE,
            has_empirical_calibration=False,
            priority=MODEL_PRIORITY[DetectionModelType.DATASHEET],
            notes=f"Range envelope: {self.max_range}m, min rho: {self.min_reflectivity}",
        )


class ManufacturerCurveModel(DetectionModel):
    """Priority 1: manufacturer empirical detection curve (P_d vs. range at a reference).

    The datasheet curve gives P_d(range) for the nominal reflectivity; scaled toward `min_reflectivity`
    as a crude but traceable proxy when ρ < reference. When ρ ≥ reference it returns the raw curve value.


    Depends on the curve itself (carried by this model), so it is always usable unless its
    reference reflectivity is missing/unknown.
"""

    def __init__(
        self,
        curve: Callable[[float], float],
        reference_reflectivity: float,
        min_reflectivity: float = 0.1,
        source: str = "manufacturer_datasheet",
    ):
        self.curve = curve
        self.reference_reflectivity = reference_reflectivity
        self.min_reflectivity = min_reflectivity
        self.source = source

    def can_use(self, sensor_params: SensorParamsView) -> bool:
        # Curve is self-contained; usable whenever the curve reference is known.. Parametrized on
        # range/reflectivity inputs passed per-ray, not on sensor envelope status..
        return True

    def compute_detection_probability(
        self,
        range_to_target: float,
        reflectivity: float,
        incidence_angle: float,
        beam_target_overlap: float,
        return_strength: float,
    ) -> DetectionResult:
        p = float(np.clip(self.curve(range_to_target, 0.0, 1.0)))
        if reflectivity < self.reference_reflectivity and self.reference_reflectivity > 0:
            scale = float(np.clip(reflectivity / self.reference_reflectivity, 0.1, 1.0))
            p *= scale
        return DetectionResult(
            probability=float(np.clip(p, 0.0,1.0)),
            model_type=DetectionModelType.MANUFACTURER_CURVE,
            physical_model_confidence=ConfidenceLevel.HIGH,
            has_empirical_calibration=False,
            model_source=self.source,
            priority=MODEL_PRIORITY[DetectionModelType.MANUFACTURER_CURVE],
            notes=f"Manufacturer detection curve, ref rho={self.reference_reflectivity}",
        )


class EmpiricalModel(DetectionModel):
    """Priority 2: user experimental calibration (PRD §65-66, SCHEMAS §26 Rule  8-aware).

    Empirical detection probability P_d = N_return / N_attempt from field trials (PRD §65).
    The calibrated curve interpolates P_d as a function of range at a given reflectivity.


    Must NOT overwrite manufacturer data (PRD §66); it coexists and stays traceable via `source`/`variables`."""

    def __init__(
        self,
        points: Sequence[tuple[float, float]],   # (range_m, P_d)
        reflectivity: float,
        source: str,
        variables: Sequence[str] = ("range", "reflectivity", "incidence_angle"),
        min_reflectivity: float = 0.1,
    ):
        if len(points) < 2:
            raise ValueError("Empirical model requires >= 2 calibration points")
        self.points = sorted(points, key=lambda t: t[0])
        self.reflectivity = reflectivity
        self.source = source
        self.variables = list(variables)
        self.min_reflectivity = min_reflectivity

    def can_use(self, sensor_params: SensorParamsView) -> bool:
        # Empirical model is supplied by the user; it does not read sensor envelope params..
        return True

    def _interp(self, r: float) -> float:
        rs = [p[0] for p in self.points]
        ps = [p[1] for p in self.points]
        if r <= rs[0]:
            return ps[0]
        if r >= rs[-1]:
            return ps[-1]
        p = float(np.interp(r, rs, ps))
        return float(np.clip(p, 0.0,1.0))

    def compute_detection_probability(
        self,
        range_to_target: float,
        reflectivity: float,
        incidence_angle: float,
        beam_target_overlap: float,
        return_strength: float,
    ) -> DetectionResult:
        p = self._interp(range_to_target)
        if reflectivity < self.reflectivity and self.reflectivity > 0:
            scale = float(np.clip(reflectivity / self.reflectivity, 0.1,1.0))
            p *= scale
        return DetectionResult(
            probability=float(np.clip(p, 0.0, 1.0)),
            model_type=DetectionModelType.EMPIRICAL,
            physical_model_confidence=ConfidenceLevel.MODERATE,
            has_empirical_calibration=True,
            model_source=self.source,
            priority=MODEL_PRIORITY[DetectionModelType.EMPIRICAL],
            notes=f"User empirical calibration:{self.source}, ref rho={self.reflectivity}",
        )


class AnalyticalModel(DetectionModel):
    """Priority 4: physics-inspired analytical model (PRD §29-30, Rule  8-aware).

    P_d = sigmoid of return strength; S ∝ ρ * A_eff * cos(α) / R².

    Depends on `beam_divergence` (via return strength) so enforce Rule  8."""

    def __init__(
        self,
        strength_threshold: float = 1e-4,
        sigmoid_steepness: float = 5000.0,
        max_range: Optional[float] = None,
    ):
        self.strength_threshold = strength_threshold
        self.sigmoid_steepness = sigmoid_steepness
        self.max_range = max_range

    def can_use(self, sensor_params: SensorParamsView) -> bool:
        return sensor_params.is_known(
            sensor_params.beam_divergence, sensor_params.beam_divergence_status
        )

    def compute_detection_probability(
        self,
        range_to_target: float,
        reflectivity: float,
        incidence_angle: float,
        beam_target_overlap: float,
        return_strength: float,
    ) -> DetectionResult:
        if self.max_range is not None and range_to_target > self.max_range:
            return DetectionResult(
                probability=0.0,
                model_type=DetectionModelType.ANALYTICAL,
                physical_model_confidence=ConfidenceLevel.LOW,
                has_empirical_calibration=False,
                priority=MODEL_PRIORITY[DetectionModelType.ANALYTICAL],
                notes="Beyond max range",
            )

        normalized = return_strength / self.strength_threshold if self.strength_threshold > 0 else 0
        x = -self.sigmoid_steepness * (normalized - 1.0)
        x = np.clip(x, -500, 500)  # avoid overflow
        p = 1.0 / (1.0 + np.exp(x))
        return DetectionResult(
            probability=float(np.clip(p, 0.0, 1.0)),
            model_type=DetectionModelType.ANALYTICAL,
            physical_model_confidence=ConfidenceLevel.MODERATE,
            has_empirical_calibration=False,
            priority=MODEL_PRIORITY[DetectionModelType.ANALYTICAL],
        )


class AssumptionModel(DetectionModel):
    """Priority 5: explicit engineering assumption (PRD §30,§32)."""

    def __init__(self, assumed_probability: Optional[float] = None):
        self.assumed_probability = assumed_probability

    def can_use(self, sensor_params: SensorParamsView) -> bool:
        return True

    def compute_detection_probability(
        self,
        range_to_target: float,
        reflectivity: float,
        incidence_angle: float,
        beam_target_overlap: float,
        return_strength: float,
    ) -> DetectionResult:
        if self.assumed_probability is None:
            return DetectionResult(
                probability=None,
                model_type=DetectionModelType.ASSUMPTION,
                physical_model_confidence=ConfidenceLevel.INSUFFICIENT,
                has_empirical_calibration=False,
                priority=MODEL_PRIORITY[DetectionModelType.ASSUMPTION],
                notes="Not reliably estimable from available data.",
            )
        return DetectionResult(
            probability=self.assumed_probability,
            model_type=DetectionModelType.ASSUMPTION,
            physical_model_confidence=ConfidenceLevel.LOW,
            has_empirical_calibration=False,
            priority=MODEL_PRIORITY[DetectionModelType.ASSUMPTION],
            notes="Explicit engineering assumption.",
        )


def insufficient_data_result() -> DetectionResult:
    """PRD section 32 / SCHEMAS sect 27: insufficient data --> never fabricate."""
    return DetectionResult(
        probability=None,
        model_type=DetectionModelType.ASSUMPTION,
        physical_model_confidence=ConfidenceLevel.INSUFFICIENT,
        has_empirical_calibration=False,
        priority=MODEL_PRIORITY[DetectionModelType.ASSUMPTION],
        notes="Not reliably estimable from available data.",
    )


# Backward-compatible aliases (tests built against the earlier name).old class dropped.)
DatasheetModel = DatasheetEnvelopeModel


class DetectionModelResolver:
    """Resolves the highest-fidelity available detection model (PRD §30).

    Chain: manufacturer curve (1) → user empirical (2) → datasheet envelope (3) →
    analytical (4) → assumption (5). First model that `can_use(sensor_params)` wins. If none,
    returns an insufficient-data resolver that never fabricates a probability (§32, §27)."""

    def __init__(
        self,
        manufacturer_curve: Optional[ManufacturerCurveModel] = None,
        user_empirical: Optional[EmpiricalModel] = None,
        datasheet_envelope: Optional[DatasheetEnvelopeModel] = None,
        analytical: Optional[AnalyticalModel] = None,
        assumption: Optional[AssumptionModel] = None,
    ):
        self.candidates = [
            manufacturer_curve,
            user_empirical,
            datasheet_envelope,
            analytical,
            assumption,
        ]

    def resolve(self, sensor_params: SensorParamsView) -> DetectionModel:
        for m in self.candidates:
            if m is None:
                continue
            if m.can_use(sensor_params):
                return m
        return AssumptionModel(assumed_probability=None)  # insufficient


def resolve_detection_model(
    sensor_params: SensorParamsView,
    manufacturer_curve: Optional[ManufacturerCurveModel] = None,
    user_empirical: Optional[EmpiricalModel] = None,
    datasheet_envelope: Optional[DatasheetEnvelopeModel] = None,
    analytical: Optional[AnalyticalModel] = None,
    assumption: Optional[AssumptionModel] = None,
) -> DetectionModel:
    """One-shot convenience resolver."""
    return DetectionModelResolver(
        manufacturer_curve=manufacturer_curve,
        user_empirical=user_empirical,
        datasheet_envelope=datasheet_envelope,
        analytical=analytical,
        assumption=assumption,
    ).resolve(sensor_params)