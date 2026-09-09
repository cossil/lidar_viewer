"""Analysis engine: sensor comparison, suitability evaluation, metrics.

PRD sections 45-54.
"""

from .comparison import (
    SensorComparisonEntry,
    SensorComparisonResult,
    compare_sensors,
)
from .metrics import SecondaryMetrics, compute_secondary_metrics
from .suitability import (
    SuitabilityEvaluation,
    evaluate_suitability,
    to_suitability_result,
)

__all__ = [
    "SensorComparisonEntry",
    "SensorComparisonResult",
    "compare_sensors",
    "SecondaryMetrics",
    "compute_secondary_metrics",
    "SuitabilityEvaluation",
    "evaluate_suitability",
    "to_suitability_result",
]