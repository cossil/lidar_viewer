"""Simulation model (SCHEMAS section 8."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import ErrorDefinition, JobStatus, SimulationMode, DataOrigin


class MonteCarlo(BaseModel):
    """Monte-Carlo trial configuration."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    enabled: bool
    trials: int = Field(default=10000, ge=1, le=100000)
    random_seed: Optional[int] = None


class Criterion(BaseModel):
    """Detection/reliable criterion."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_returns: int = Field(ge=1)
    minimum_probability: float = Field(ge=0.0, le=1.0)


class CharacterizationCriterion(Criterion):
    """Characterization criterion (extends base criterion."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_coverage: float = Field(ge=0.0, le=1.0)
    maximum_range_uncertainty: Optional[float] = Field(default=None, ge=0.0)


class DetectionCriteria(BaseModel):
    """detected / reliable / characterized criteria."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    detected: Optional[Criterion] = None
    reliable: Optional[Criterion] = None
    characterized: Optional[CharacterizationCriterion] = None


class MeasurementModel(BaseModel):
    """Measurement error model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    range_bias: float = 0.0
    range_sigma: Optional[float] = Field(default=None, ge=0.0)
    range_error_definition: Optional[ErrorDefinition] = None
    angular_bias: float = 0.0
    angular_sigma: Optional[float] = Field(default=None, ge=0.0)


class SimulationAssumption(BaseModel):
    """Assumption attached to a simulation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str
    description: str
    origin: Optional[Literal["ASSUMED", "USER_DEFINED"]] = None


class Simulation(BaseModel):
    """Execution of a scenario using a particular model configuration."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    simulation_id: str
    scenario_id: str
    sensor_id: str
    sensor_version: Optional[str] = None
    mode: SimulationMode
    duration: float = Field(gt=0.0)
    monte_carlo: MonteCarlo
    random_seed: Optional[int] = 123456
    detection_model_id: Optional[str] = None
    detection_criteria: Optional[DetectionCriteria] = None
    measurement_model: Optional[MeasurementModel] = None
    assumptions: List[SimulationAssumption] = Field(default_factory=list)
    software_version: Optional[str] = None
    model_version: Optional[str] = None
    status: JobStatus = Field(default=JobStatus.QUEUED)