"""Application profile and suitability models (SCHEMAS sections 10-11."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import Suitability


class TargetSpec(BaseModel):
    """DBH target envelope."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_dbh: float
    maximum_dbh: float


class OperationalRange(BaseModel):
    """Operational distance range."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum: float
    maximum: float


class Requirements(BaseModel):
    """Suitability requirements."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_detection_probability: float = Field(ge=0.0, le=1.0)
    minimum_reliable_probability: float = Field(ge=0.0, le=1.0)
    minimum_coverage: float = Field(ge=0.0, le=1.0)
    maximum_range_uncertainty: float = Field(ge=0.0)


class ApplicationProfile(BaseModel):
    """A forest-inventory suitability profile."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    profile_id: str
    name: str
    target: TargetSpec
    operational_range: OperationalRange
    requirements: Requirements


class CriterionResult(BaseModel):
    """Individual suitability criterion evaluation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    criterion: str
    required: float
    measured: float
    passed: bool


class SuitabilityResult(BaseModel):
    """Aggregate suitability assessment."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    classification: Suitability
    criteria: List[CriterionResult] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)