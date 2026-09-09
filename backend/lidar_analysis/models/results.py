"""Simulation results model (SCHEMAS section 9."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

import math

from .common import ConfidenceLevel

PI_HALF = math.pi / 2.0


class Metrics(BaseModel):
    """Summary statistics metrics block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    detection_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reliable_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    characterization_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    expected_target_returns: Optional[float] = Field(default=None, ge=0.0)
    geometric_coverage: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    target_angular_size: Optional[float] = Field(default=None, ge=0.0)
    beam_footprint: Optional[float] = Field(default=None, ge=0.0)
    incidence_angle: Optional[float] = Field(default=None, ge=0.0, le=PI_HALF)
    range_uncertainty: Optional[float] = Field(default=None, ge=0.0)


class EffectiveRanges(BaseModel):
    """Effective detection ranges block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    detection: Optional[float] = None
    reliable: Optional[float] = None
    characterization: Optional[float] = None


class ModelConfidence(BaseModel):
    """Confidence metadata block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    physical_model: ConfidenceLevel
    detection_model: Optional[ConfidenceLevel] = None
    monte_carlo_precision: Optional[Literal["high", "moderate", "low"]] = None


class Distribution(BaseModel):
    """Monte-Carlo result distribution."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    mean: float
    median: float
    std: float
    min: float
    max: float
    p05: float
    p25: float
    p75: float
    p95: float


class Sweep(BaseModel):
    """Parameter-sweep metadata."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    type: Optional[Literal["distance", "dbh", "reflectivity", "incidence_angle"]] = None
    parameter: Optional[str] = None
    values: List[float] = Field(default_factory=list)
    results: List[dict] = Field(default_factory=list)


class Point(BaseModel):
    """A single synthetic point-cloud point."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    x: float
    y: float
    z: float
    true_range: Optional[float] = None
    measured_range: Optional[float] = None
    range_error: Optional[float] = None
    azimuth: Optional[float] = None
    elevation: Optional[float] = None
    incidence_angle: Optional[float] = None
    detection_probability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    trial_id: Optional[int] = None
    target_surface: Optional[str] = None


class PointCloud(BaseModel):
    """Synthetic point-cloud block."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    count: int = Field(ge=0)
    points: List[Point] = Field(default_factory=list)


class Results(BaseModel):
    """Simulation results container."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    simulation_id: str
    status: Literal["completed", "failed"]
    metrics: Metrics
    effective_ranges: Optional[EffectiveRanges] = None
    model_confidence: ModelConfidence
    distribution: Optional[Distribution] = None
    sweep: Optional[Sweep] = None
    point_cloud: Optional[PointCloud] = None
    warnings: List[str] = Field(default_factory=list)