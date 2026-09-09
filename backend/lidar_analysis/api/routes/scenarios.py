"""Scenario routes (PRD section 58).

GET    /api/scenarios
POST   /api/scenarios
GET    /api/scenarios/{id}
PUT    /api/scenarios/{id}
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ...models.scenario import Scenario
from ..store import store

router = APIRouter()


@router.get("", response_model=List[dict])
def list_scenarios():
    """List all scenarios."""
    return [s.model_dump() for s in store.list_scenarios()]


@router.post("", status_code=201)
def create_scenario(scenario: Scenario):
    """Create a new scenario."""
    sid = store.put_scenario(scenario)
    return {"scenario_id": sid, "status": "created"}


@router.get("/{scenario_id}")
def get_scenario(scenario_id: str):
    """Get a scenario by ID."""
    scenario = store.get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
    return scenario.model_dump()


@router.put("/{scenario_id}", status_code=200)
def update_scenario(scenario_id: str, scenario: Scenario) -> dict:
    """Update an existing scenario by ID."""
    if store.get_scenario(scenario_id) is None:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
    updated = scenario.model_copy(update={"scenario_id": scenario_id})
    store.put_scenario(updated)
    return {"scenario_id": scenario_id, "status": "updated"}