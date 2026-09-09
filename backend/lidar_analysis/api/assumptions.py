"""Assumption registry (PRD section 61; Simulation->Assumptions relationship, section 29).

Simulation results reference the explicit engineering assumptions used to produce them.
This lightweight in-memory registry stores canonical assumptions so a simulation
result can carry a list of `assumption_<8hex>` ids resolvable to their descriptions.
(Simulation -- Assumptions, one-to-many reference, PRD section 29).
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional


class AssumptionRegistry:
    """In-memory registry of engineering assumptions referenced by simulation results."""

    def __init__(self) -> None:
        self._assumptions: Dict[str, dict] = {}

    def register(self, assumption: dict) -> str:
        """Register an assumption dict-and return its id `assumption_<8hex>`."""
        assumption_id = f"assumption_{uuid.uuid4().hex[:8]}"
        self._assumptions[assumption_id] = assumption
        return assumption_id

    def list(self) -> List[dict]:
        """Return all registered assumptions."""
        return list(self._assumptions.values())

    def get(self, assumption_id: str) -> Optional[dict]:
        """Fetch a registered assumption by id."""
        return self._assumptions.get(assumption_id)


# Canonical assumptions used by the default simulation pipeline (datasheet-envelope fallback).
_DEFAULT_ASSUMPTIONS = [
    {
        "description": "measurement model: additive Gaussian noise",
        "reason": "standard additive Gaussian measurement error model when sensor noise specs are unavailable",
    },
    {
        "description": "detection model: datasheet envelope fallback",
        "reason": "using the datasheet max-range envelope when no empirical detection curve exists",
    },
    {
        "description": "beam divergence: default 0.003 rad if unspecified",
        "reason": "typical rotating LiDAR beam divergence when sensor beam data is missing",
    },
    {
        "description": "coverage: angular bounding-box approximation",
        "reason": "FOV coverage approximated by the angular extent of the scanned target",
    },
]


def record_default_assumptions(sim_id: str, extra: Optional[dict] = None) -> List[str]:
    """Register the canonical assumptions for a simulation run-and return their ids.



    Any `extra` assumption dict-is passed through-and tagged with thesame simulation_id.
    """
    ids = []
    for a in _DEFAULT_ASSUMPTIONS:
        rec = dict(a)
        rec["simulation_id"] = sim_id
        ids.append(ASSUMPTION_REGISTRY.register(rec))
    if extra:
        rec = dict(extra)
        rec["simulation_id"] = sim_id
        ids.append(ASSUMPTION_REGISTRY.register(rec))
    return ids


# Module-level default registry (shared across the API process).
ASSUMPTION_REGISTRY = AssumptionRegistry()