"""PUT /api/scenarios/{scenario_id} tests (PRD section 58).

Tests:
  - Update an existing scenario and reflect the change via GET
  - Return 404 for an unknown scenario id

NOTE: Kept in a separate file to avoid clobbering parallel edits to test_api.py.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lidar_analysis.api.app import create_app
from lidar_analysis.api.store import store


@pytest.fixture()
def client():
    """Create a fresh test client with a clean store."""
    store._sensors.clear()
    store._scenarios.clear()
    store._simulations.clear()
    store._jobs.clear()
    app = create_app()
    yield TestClient(app)
    store._sensors.clear()
    store._scenarios.clear()
    store._simulations.clear()
    store._jobs.clear()


@pytest.fixture()
def sample_scenario_data():
    """A minimal valid scenario dict matching the actual Pydantic Scenario model."""
    return {
        "scenario_id": "test-scenario-001",
        "sensor_id": "hesai-qt64",
        "environment": {"atmosphere": "clear"},
        "sensor_pose": {
            "position": [0, 0, 1.5],
            "orientation": {"yaw": 0, "pitch": 0, "roll": 0},
        },
        "target": {
            "type": "cylinder",
            "position": [30, 0, 0.5],
            "orientation": [0, 0, 1],
            "diameter": 0.10,
            "reflectivity": 0.3,
        },
    }


class TestScenarioPut:
    def test_update_scenario(self, client, sample_scenario_data):
        """PUT updates an existing scenario and GET reflects the change."""
        resp = client.post("/api/scenarios", json=sample_scenario_data)
        assert resp.status_code == 201

        updated = dict(sample_scenario_data)
        updated["target"] = {
            "type": "box",
            "position": [10, 20, 30],
            "orientation": [0, 0, 1],
            "width": 1.0,
            "depth": 0.5,
            "height": 2.0,
            "reflectivity": 0.8,
        }
        resp = client.put("/api/scenarios/test-scenario-001", json=updated)
        assert resp.status_code == 200
        assert resp.json() == {
            "scenario_id": "test-scenario-001",
            "status": "updated",
        }

        got = client.get("/api/scenarios/test-scenario-001").json()
        assert got["target"]["type"] == "box"
        assert got["target"]["reflectivity"] == 0.8
        assert got["scenario_id"] == "test-scenario-001"

    def test_update_scenario_not_found(self, client, sample_scenario_data):
        """PUT to a nonexistent scenario returns 404."""
        resp = client.put("/api/scenarios/nonexistent", json=sample_scenario_data)
        assert resp.status_code == 404