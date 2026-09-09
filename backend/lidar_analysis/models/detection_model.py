"""DetectionModel model (SCHEMAS section 7."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .provenance import Provenance


DetectionModelType = Literal["datasheet", "analytical", "empirical", "assumption"]


class Validity(BaseModel):
    """Validity envelope for a detection model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    minimum_range: Optional[float] = None
    maximum_range: Optional[float] = None
    minimum_reflectivity: Optional[float] = None
    maximum_reflectivity: Optional[float] = None
    notes: Optional[str] = None


class DetectionModel(BaseModel):
    """An independent detection model object."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    model_id: str
    model_type: DetectionModelType
    version: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required_inputs: List[str] = Field(default_factory=list)
    output: str = "probability"
    validity: Optional[Validity] = None
    provenance: Optional[Provenance] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)