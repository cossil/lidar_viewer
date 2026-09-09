"""Named Detection Model Registry (PRD §30-32, §66; SCHEMAS §7).

Allows selecting detection models by ID in simulation requests:
- datasheet_envelope: Default conservative envelope based on max range & beam divergence.
- analytical_physics: Physics-inspired analytical sigmoid detection model.
- empirical_calibrated: Empirical detection curve / user calibration.
- assumption_fixed: Explicit fixed engineering assumption (P_d = 1.0 or custom).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from ..physics.detection import (
    AnalyticalModel,
    AssumptionModel,
    DatasheetModel,
    DetectionModel,
    EmpiricalModel,
)
from .errors import ApiError


class DetectionModelRegistry:
    """Registry mapping model IDs to factories or instances."""

    def __init__(self):
        self._descriptions = {
            "datasheet_envelope": "Manufacturer range/reflectivity envelope (conservative)",
            "analytical_physics": "Physics-inspired analytical sigmoid detection model",
            "empirical_calibrated": "Empirical detection curve / experimental calibration",
            "assumption_fixed": "Explicit engineering assumption (fixed detection probability)",
        }

    def list_models(self) -> List[Dict[str, Any]]:
        """List registered model IDs and descriptions."""
        return [
            {"model_id": mid, "description": desc}
            for mid, desc in self._descriptions.items()
        ]

    def resolve(
        self,
        model_id: Optional[str],
        sensor: Any,
        **kwargs: Any,
    ) -> DetectionModel:
        """Resolve a detection model instance for a sensor and optional model ID."""
        max_range = 200.0
        if sensor and sensor.range and sensor.range.maximum and sensor.range.maximum.value is not None:
            max_range = float(sensor.range.maximum.value)

        # Default model if none specified
        if not model_id or model_id == "datasheet_envelope":
            return DatasheetModel(max_range=max_range)

        if model_id == "analytical_physics":
            return AnalyticalModel(strength_threshold=1e-4, sigmoid_steepness=5000.0, max_range=max_range)

        if model_id == "assumption_fixed":
            prob = kwargs.get("assumed_probability", 1.0)
            return AssumptionModel(assumed_probability=prob)

        if model_id == "empirical_calibrated":
            # If empirical calibration points provided or default curve
            ranges = kwargs.get("ranges", [0.0, max_range * 0.5, max_range, max_range * 1.2])
            probabilities = kwargs.get("probabilities", [1.0, 0.98, 0.5, 0.0])
            return EmpiricalModel(ranges=ranges, probabilities=probabilities)

        raise ApiError(
            status_code=422,
            code="INVALID_DETECTION_MODEL",
            message=f"Unknown detection model ID '{model_id}'. Registered models: {list(self._descriptions.keys())}",
            field="detection_model_id",
        )


detection_registry = DetectionModelRegistry()
