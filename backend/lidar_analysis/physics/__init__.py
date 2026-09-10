"""Physics engine: beam overlap, detection models, measurement model.

PRD sections 25-34.
"""

from .beam import beam_target_overlap, effective_illuminated_area_cylinder, return_strength
from .detection import (
    AnalyticalModel,
    AssumptionModel,
    DatasheetModel,
    DetectionModel,
    DetectionModelType,
    DetectionResult,
    insufficient_data_result,
)
from .measurement import (
    MeasurementConfig,
    MeasurementModel,
    MeasurementSample,
    convert_sigma,
    compute_parametric_range_noise,
)

__all__ = [
    "beam_target_overlap",
    "return_strength",
    "effective_illuminated_area_cylinder",
    "DetectionModel",
    "DetectionModelType",
    "DetectionResult",
    "DatasheetModel",
    "AnalyticalModel",
    "AssumptionModel",
    "insufficient_data_result",
    "MeasurementConfig",
    "MeasurementModel",
    "MeasurementSample",
    "convert_sigma",
    "compute_parametric_range_noise",
]