"""Datasheet routes (PRD sections 11-12; SCHEMAS sections 14-15.

POST /api/datasheets/extract
POST /api/datasheets/{extraction_id}/validate
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from ...ingestion import ingest_datasheet, validate_datasheet

router = APIRouter()


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    filename: str
    content_type: str
    data: Dict[str, Any] = {}


class ValidateRequest(BaseModel):
    validated_parameters: Dict[str, Any]


@router.post("/extract", status_code=200)
def extract_datasheet(request: ExtractRequest):
    data = request.data
    if not data:
        extra = dict(getattr(request, "model_extra", None) or {})
        if "body" in extra and isinstance(extra["body"], dict):
            data = extra["body"]
        else:
            data = {k: v for k, v in extra.items() if k not in ("filename", "content_type", "data")}
    ctype = (request.content_type or "").lower()
    is_text = any(tok in ctype for tok in ("plain", "text", "pdf"))
    if is_text and isinstance(data.get("text"), str):
        result = ingest_datasheet(data["text"], request.filename, request.content_type)
    else:
        if isinstance(data, dict):
            data = {k: v for k, v in data.items() if k != "text"}
        result = ingest_datasheet(data, request.filename, request.content_type)
    return result


@router.post("/{extraction_id}/validate", status_code=200)
def validate_extraction(extraction_id: str, request: ValidateRequest):
    try:
        return validate_datasheet(extraction_id, request.validated_parameters)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Extraction {extraction_id} not found")