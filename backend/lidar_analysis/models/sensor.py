"""Sensor model (SCHEMAS section 5."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import SensorType, ValidationStatus
from .parameter import Parameter
from .provenance import Provenance


class Range(BaseModel):
    """Range specification block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum: Optional[Parameter] = None
    maximum: Optional[Parameter] = None
    max_representable_range: Optional[Parameter] = None
    reflectivity_curves: List["RangeCurve"] = Field(default_factory=list)


class RangeCurve(BaseModel):
    """Range-vs-reflectivity curve point."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    reflectivity: Parameter
    maximum_range: Parameter
    conditions: Optional[str] = None


class Accuracy(BaseModel):
    """Accuracy block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    range: Optional[Parameter] = None
    angular: Optional[Parameter] = None
    definition: Optional[str] = None


class Precision(BaseModel):
    """Precision block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    range: Optional[Parameter] = None
    range_min: Optional[Parameter] = None
    range_max_10pct: Optional[Parameter] = None
    angular: Optional[Parameter] = None
    definition: Optional[str] = None


class Angular(BaseModel):
    """Angular characteristics block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    horizontal_fov: Optional[Parameter] = None
    vertical_fov: Optional[Parameter] = None
    horizontal_resolution: Optional[Parameter] = None
    vertical_resolution: Optional[Parameter] = None
    horizontal_uncertainty: Optional[Parameter] = None
    vertical_uncertainty: Optional[Parameter] = None
    channel_count: Optional[Parameter] = None
    channel_angles: List[Parameter] = Field(default_factory=list)


class Beam(BaseModel):
    """Beam characteristics block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    horizontal_divergence: Optional[Parameter] = None
    vertical_divergence: Optional[Parameter] = None
    beam_shape: Optional[Literal["circular", "elliptical", "gaussian", "unknown"]] = None


class Scan(BaseModel):
    """Scanning characteristics block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    type: SensorType
    point_rate: Optional[Parameter] = None
    frame_rate: Optional[Parameter] = None
    rotation_frequency: Optional[Parameter] = None
    horizontal_resolution: Optional[Parameter] = None
    vertical_resolution: Optional[Parameter] = None
    scan_phase: Optional[Parameter] = None
    coverage_model: Optional[str] = None
    returns_per_pulse: Optional[int] = Field(default=1, ge=1)


class Optical(BaseModel):
    """Optical characteristics block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    wavelength: Optional[Parameter] = None
    receiver_aperture: Optional[Parameter] = None
    pulse_energy: Optional[Parameter] = None


class Assumption(BaseModel):
    """An engineering assumption attached to a sensor."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str
    description: str
    reason: Optional[str] = None


class DetectionModelReference(BaseModel):
    """Detection characteristics block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    default_model: Optional[Literal["datasheet", "analytical", "empirical", "assumption"]] = None
    threshold: Optional[Parameter] = None
    empirical_curves: List[dict] = Field(default_factory=list)


class Validation(BaseModel):
    """Sensor validation status block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    status: ValidationStatus
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None


class Sensor(BaseModel):
    """A validated LiDAR sensor model (sensor.json, SCHEMAS section 5."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    sensor_id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    manufacturer: str = Field(min_length=1)
    model: str = Field(min_length=1)
    hardware_revision: Optional[str] = None
    firmware_version: Optional[str] = None
    version: str
    sensor_type: SensorType
    wavelength: Optional[Parameter] = None
    range: Range
    accuracy: Optional[Accuracy] = None
    precision: Optional[Precision] = None
    angular: Optional[Angular] = None
    beam: Optional[Beam] = None
    scan: Scan
    optical: Optional[Optical] = None
    detection: Optional[DetectionModelReference] = None
    provenance: List[Provenance] = Field(default_factory=list)
    assumptions: List[Assumption] = Field(default_factory=list)
    validation: Validation


    @model_validator(mode="after")
    def _check_sensor_type_matches_scan(self) -> "Sensor":
        if self.sensor_type != self.scan.type:
            raise ValueError("sensor_type must match scan.type")
        return self

Range.model_rebuild()