"""Parameter value model (SCHEMAS section 4."""

from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, model_validator

from .common import DataOrigin, ParameterStatus
from .provenance import Provenance


class Parameter(BaseModel):
    """A single sensor parameter wrapped with unit, origin, status and provenance."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


    value: Union[float, int, None]
    unit: Optional[str]
    origin: DataOrigin
    status: ParameterStatus = ParameterStatus.KNOWN
    definition: Optional[str] = None
    conditions: Optional[str] = None
    provenance: Optional[Provenance] = None


    @model_validator(mode="after")
    def _check_unknown_and_value(self) -> "Parameter":
        if self.status == ParameterStatus.UNKNOWN:
            if self.value is not None:
                raise ValueError("status 'unknown' requires value=None")
        elif self.status == ParameterStatus.KNOWN:
            if self.value is None:
                raise ValueError("a 'known' parameter must have a numeric value")
        return self