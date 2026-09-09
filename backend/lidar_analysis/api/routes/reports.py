"""Report routes (PRD section 60; SCHEMAS section24.

POST   /api/reports
GET    /api/reports/{report_id}
"""

from __future__ import annotations

import uuid

from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..store import store
from ...reporting import export_json, generate_markdown_report

router = APIRouter()


_REPORTS: Dict[str, str] = {}


class ReportRequest(BaseModel):
    simulation_id: str
    format: str = "markdown"
    include: Dict[str, bool] = {}


@router.post("")
def create_report(request: ReportRequest):
    job = store.get_job(request.simulation_id)
    if job is None or job.result is None:
        raise HTTPException(status_code=404, detail=f"Simulation {request.simulation_id} not found")

    if request.format not in ("markdown", "json"):
        raise HTTPException(status_code=422, detail="format must be 'markdown' or 'json'")

    result = job.result
    if request.format == "json":
        body = export_json(result)
    else:
        body = generate_markdown_report(
            title=f"LiDAR Engineering Report -- {request.simulation_id}",
            results=result,
            simulation_config={"simulation_id": request.simulation_id},
        )

    report_id = f"report_{uuid.uuid4().hex[:8]}"
    _REPORTS[report_id] = {
        "format": request.format,
        "body": body,
    }
    return {"report_id": report_id, "status": "completed", "format": request.format}


@router.get("/{report_id}")
def get_report(report_id: str):
    if report_id not in _REPORTS:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    entry = _REPORTS[report_id]
    return {
        "report_id": report_id,
        "status": "completed",
        "format": entry["format"],
        "body": entry["body"],
    }