"""Provenance model (SCHEMAS section 3.

Every externally derived sensor parameter carries a Provenance.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import DataOrigin

ExtractionMethod = Literal["manual", "ai", "parser", "calculation", "experiment", "import"]


class Provenance(BaseModel):
    """Source and validation metadata for an externally-sourced parameter."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)



    origin: DataOrigin
    user_validated: bool
    document: Optional[str] = None
    document_version: Optional[str] = None
    page: Optional[int] = Field(default=None, ge=1)
    section: Optional[str] = None
    source_reference: Optional[str] = None
    source_text: Optional[str] = None
    extraction_method: Optional[ExtractionMethod] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    validation_timestamp: Optional[datetime] = None
    notes: Optional[str] = None