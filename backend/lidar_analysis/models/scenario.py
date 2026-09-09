"""Scenario model (SCHEMAS section 6."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

import math


class Position(BaseModel):
    """A length-3 position array."""

    root: List[float] = Field(min_length=3, max_length=3)


class Orientation(BaseModel):
    """Sensor orientation with pitch clamped to +/- pi/2."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    yaw: float
    pitch: float
    roll: float


    @field_validator("pitch")
    @classmethod
    def _clamp_pitch(cls, v: float) -> float:
        half = math.pi / 2.0
        if v <  -half or v > half:
            raise ValueError("pitch must be within +/-pi/2")
        return v


class Pose(BaseModel):
    """Sensor pose: position and orientation."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    position: List[float] = Field(min_length=3, max_length=3)
    orientation: Orientation


class Target(BaseModel):
    """Simulation target (box or cylinder)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    type: Literal["box", "cylinder"]
    position: List[float] = Field(min_length=3, max_length=3)
    orientation: List[float] = Field(min_length=3, max_length=3)
    width: Optional[float] = Field(default=None, gt=0.0)
    depth: Optional[float] = Field(default=None, gt=0.0)
    height: Optional[float] = Field(default=None, gt=0.0)
    diameter: Optional[float] = Field(default=None, ge=0.05, le=1.0)
    reflectivity: float = Field(ge=0.1, le=1.0)


    @field_validator("type")
    @classmethod
    def _check_dimension_consistency(cls, v: str, info) -> str:
        if v == "box":
            for name in ("width", "depth", "height"):
                val = info.data.get(name)
                if val is None:
                    # width/depth/height optional per schema; leave alone
                    pass
        return v


class Environment(BaseModel):
    """MVP atmospheric / occlusion conditions (all const false."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    atmosphere: Literal["clear"] = "clear"
    rain: bool = False
    fog: bool = False
    dust: bool = False
    vegetation_occlusion: bool = False
    terrain_occlusion: bool = False


class Randomization(BaseModel):
    """Optional randomization toggles."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    sensor_pose: bool = False
    target_pose: bool = False
    reflectivity: bool = False
    scan_phase: bool = False


class Scenario(BaseModel):
    """A scenario describes the physical experiment being simulated."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    scenario_id: str
    name: Optional[str] = None
    sensor_id: str
    sensor_pose: Pose
    target: Target
    environment: Environment
    randomization: Optional[Randomization] = None
    application_profile_id: Optional[str] = None