"""Common enumerated types used across the LiDAR analysis platform.

Strictly matches SCHEMAS section 2 "Common Enumerations" (2.1).
"""

from __future__ import annotations

from enum import Enum


class DataOrigin(str, Enum):
    """Origin of a parameter value (SCHEMAS 2.1)."""
    SOURCE = "SOURCE"
    USER_DEFINED = "USER_DEFINED"
    DERIVED = "DERIVED"
    ASSUMED = "ASSUMED"
    MODELED = "MODELED"
    SIMULATED = "SIMULATED"
    EMPIRICAL = "EMPIRICAL"


class ParameterStatus(str, Enum):
    """Knownness of a parameter value (SCHEMAS 2.1)."""
    KNOWN = "known"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    ESTIMATED = "estimated"


class ErrorDefinition(str, Enum):
    """Statistical definition (SCHEMAS 2.1)."""
    ONE_SIGMA = "1sigma"
    TWO_SIGMA = "2sigma"
    PERCENT_95 = "95_percent"
    RMS = "rms"
    MAXIMUM = "maximum"
    UNSPECIFIED = "unspecified"


class SensorType(str, Enum):
    """LiDAR scan architecture (SCHEMAS 2.1)."""
    MECHANICAL_SPINNING = "mechanical_spinning"
    STRUCTURED_RASTER = "structured_raster"
    NON_REPETITIVE = "non_repetitive"
    OTHER = "other"


class SimulationMode(str, Enum):
    """Simulation execution mode (SCHEMAS 2.1)."""
    ANALYTICAL = "analytical"
    MONTE_CARLO = "monte_carlo"
    SYNTHETIC_POINT_CLOUD = "synthetic_point_cloud"


class JobStatus(str, Enum):
    """Job lifecycle status (SCHEMAS 2.1)."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationStatus(str, Enum):
    """Sensor/data validation status (SCHEMAS 2.1)."""
    UNVALIDATED = "unvalidated"
    PARTIALLY_VALIDATED = "partially_validated"
    VALIDATED = "validated"


class Suitability(str, Enum):
    """Suitability classification (SCHEMAS 2.1)."""
    SUITABLE = "suitable"
    CONDITIONALLY_SUITABLE = "conditionally_suitable"
    NOT_SUITABLE = "not_suitable"
    INSUFFICIENT_DATA = "insufficient_data"


class ConfidenceLevel(str, Enum):
    """Physical-model confidence (SCHEMAS 2.1)."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INSUFFICIENT = "insufficient"