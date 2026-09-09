"""API integration tests (PRD section 58).

Tests:
  - Health endpoint
  - Sensor CRUD (create, read, update, delete, list)
  - Scenario CRUD
  - Simulation job creation and status
  - Distance sweep
  - Sensor comparison
"""

from __future__ import annotations

import math
import pytest
from fastapi.testclient import TestClient

from lidar_analysis.api.app import create_app
from lidar_analysis.api.store import store


@pytest.fixture()
def client():
    """Create a fresh test client with clean store."""
    store._sensors.clear()
    store._scenarios.clear()
    store._simulations.clear()
    store._jobs.clear()
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def sample_sensor_data():
    """A minimal valid sensor dict matching the actual Pydantic Sensor model."""
    return {
        "sensor_id": "hesai-qt64",
        "sensor_type": "mechanical_spinning",
        "manufacturer": "Hesai",
        "model": "QT64",
        "version": "1.0.0",
        "wavelength": {"value": 905, "unit": "nm", "origin": "SOURCE", "status": "known"},
        "range": {
            "maximum": {"value": 200, "unit": "m", "origin": "SOURCE", "status": "known"},
        },
        "accuracy": {
            "range": {"value": 0.02, "unit": "m", "origin": "SOURCE", "status": "known"},
        },
        "beam": {
            "horizontal_divergence": {"value": 0.003, "unit": "rad", "origin": "SOURCE", "status": "known"},
        },
        "scan": {
            "type": "mechanical_spinning",
            "point_rate": {"value": 600000, "unit": "Hz", "origin": "SOURCE", "status": "known"},
            "rotation_frequency": {"value": 10, "unit": "Hz", "origin": "SOURCE", "status": "known"},
            "frame_rate": {"value": 10, "unit": "Hz", "origin": "SOURCE", "status": "known"},
        },
        "validation": {
            "status": "validated",
        },
    }


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


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestSensorCRUD:
    def test_create_sensor(self, client, sample_sensor_data):
        resp = client.post("/api/sensors", json=sample_sensor_data)
        assert resp.status_code == 201
        assert resp.json()["sensor_id"] == "hesai-qt64"

    def test_get_sensor(self, client, sample_sensor_data):
        client.post("/api/sensors", json=sample_sensor_data)
        resp = client.get("/api/sensors/hesai-qt64")
        assert resp.status_code == 200
        assert resp.json()["sensor_id"] == "hesai-qt64"

    def test_get_sensor_not_found(self, client):
        resp = client.get("/api/sensors/nonexistent")
        assert resp.status_code == 404

    def test_list_sensors(self, client, sample_sensor_data):
        client.post("/api/sensors", json=sample_sensor_data)
        resp = client.get("/api/sensors")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_update_sensor(self, client, sample_sensor_data):
        client.post("/api/sensors", json=sample_sensor_data)
        sample_sensor_data["manufacturer"] = "Hesai Technology"
        resp = client.put("/api/sensors/hesai-qt64", json=sample_sensor_data)
        assert resp.status_code == 200

    def test_delete_sensor(self, client, sample_sensor_data):
        client.post("/api/sensors", json=sample_sensor_data)
        resp = client.delete("/api/sensors/hesai-qt64")
        assert resp.status_code == 200
        resp = client.get("/api/sensors/hesai-qt64")
        assert resp.status_code == 404

    def test_extra_field_rejected(self, client, sample_sensor_data):
        """extra='forbid' should reject unknown fields."""
        sample_sensor_data["unknown_field"] = "bad"
        resp = client.post("/api/sensors", json=sample_sensor_data)
        assert resp.status_code == 422


class TestScenarioCRUD:
    def test_create_scenario(self, client, sample_scenario_data):
        resp = client.post("/api/scenarios", json=sample_scenario_data)
        assert resp.status_code == 201

    def test_get_scenario(self, client, sample_scenario_data):
        client.post("/api/scenarios", json=sample_scenario_data)
        resp = client.get("/api/scenarios/test-scenario-001")
        assert resp.status_code == 200

    def test_list_scenarios(self, client, sample_scenario_data):
        client.post("/api/scenarios", json=sample_scenario_data)
        resp = client.get("/api/scenarios")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


def sim_request(scenario_id="test-scenario-001", **overrides):
    base = {
        "scenario_id": scenario_id,
        "mode": "monte_carlo",
        "duration": 0.01,
        "monte_carlo": {
            "enabled": True,
            "trials": 10,
            "random_seed": 42,
        },
        "detection_model_id": None,
        "measurement_model": {
            "range_bias": 0.0,
            "range_sigma": 0.0002,
            "range_error_definition": "1sigma",
        },
    }
    base.update(overrides)
    return base


class TestSimulation:
    def test_create_simulation(self, client, sample_sensor_data, sample_scenario_data):
        client.post("/api/sensors", json=sample_sensor_data)
        client.post("/api/scenarios", json=sample_scenario_data)
        resp = client.post("/api/simulations", json=sim_request())
        assert resp.status_code == 202
        body = resp.json()
        assert body["simulation_id"].startswith("sim_")
        assert body["status"] == "queued"

    def test_get_simulation(self, client, sample_sensor_data, sample_scenario_data):
        client.post("/api/sensors", json=sample_sensor_data)
        client.post("/api/scenarios", json=sample_scenario_data)
        create_resp = client.post("/api/simulations", json=sim_request())
        assert create_resp.status_code == 202
        sim_id = create_resp.json()["simulation_id"]
        resp = client.get(f"/api/simulations/{sim_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["trials_total"] == 10
        assert "result" not in data
        assert "error" not in data

    def test_get_simulation_results(self, client, sample_sensor_data, sample_scenario_data):
        client.post("/api/sensors", json=sample_sensor_data)
        client.post("/api/scenarios", json=sample_scenario_data)
        create_resp = client.post("/api/simulations", json=sim_request())
        sim_id = create_resp.json()["simulation_id"]
        resp = client.get(f"/api/simulations/{sim_id}/results")
        assert resp.status_code == 200
        data = resp.json()
        assert "p_detected" in data
        assert "detection_count_stats" in data
        assert "expected_returns_stats" in data

    def test_get_simulation_results_not_complete(self, client, sample_sensor_data, sample_scenario_data):
        client.post("/api/sensors", json=sample_sensor_data)
        client.post("/api/scenarios", json=sample_scenario_data)
        create_resp = client.post("/api/simulations", json=sim_request())
        sim_id = create_resp.json()["simulation_id"]
        store.update_job(sim_id, status="running")
        resp = client.get(f"/api/simulations/{sim_id}/results")
        assert resp.status_code == 409
        assert resp.json() == {"error": "simulation_not_complete", "status": "running"}

    def test_simulation_not_found(self, client):
        resp = client.get("/api/simulations/nonexistent")
        assert resp.status_code == 404

    def test_simulation_results_not_found(self, client):
        resp = client.get("/api/simulations/nonexistent/results")
        assert resp.status_code == 404

    def test_simulation_scenario_not_found(self, client):
        resp = client.post("/api/simulations", json=sim_request(scenario_id="nonexistent"))
        assert resp.status_code == 404

    def test_simulation_sensor_not_found(self, client, sample_scenario_data):
        client.post("/api/scenarios", json=sample_scenario_data)
        resp = client.post("/api/simulations", json=sim_request())
        assert resp.status_code == 404

    def test_simulation_mode_not_supported(self, client, sample_sensor_data, sample_scenario_data):
        client.post("/api/sensors", json=sample_sensor_data)
        client.post("/api/scenarios", json=sample_scenario_data)
        resp = client.post("/api/simulations", json=sim_request(mode="bogus_mode"))
        assert resp.status_code == 422


class TestAnalysis:
    def test_distance_sweep(self, client, sample_sensor_data, sample_scenario_data):
        client.post("/api/sensors", json=sample_sensor_data)
        client.post("/api/scenarios", json=sample_scenario_data)
        resp = client.post("/api/analysis/distance-sweep", json={
            "scenario_id": "test-scenario-001",
            "distance": {"start": 10, "end": 20, "step": 10},
            "simulation": {"duration": 0.1, "monte_carlo_trials": 5, "random_seed": 42},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["analysis_id"].startswith("sweep_")
        assert len(data["points"]) == 2
        assert "effective_ranges" in data

    def test_compare(self, client, sample_sensor_data):
        client.post("/api/sensors", json=sample_sensor_data)
        sensor2 = sample_sensor_data.copy()
        sensor2["sensor_id"] = "velodyne-vlp16"
        client.post("/api/sensors", json=sensor2)
        resp = client.post("/api/analysis/compare", json={
            "sensor_ids": ["hesai-qt64", "velodyne-vlp16"],
            "scenario": {
                "target_type": "cylinder",
                "dbh": 0.10,
                "distance": 20,
                "reflectivity": 0.3,
                "incidence_angle": 0,
            },
            "simulation": {"duration": 0.1, "monte_carlo_trials": 5, "random_seed": 42},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["comparison_id"].startswith("cmp_")
        assert len(data["sensors"]) == 2
        assert "conditions" in data
        # identical conditions guaranteed
        assert data["conditions"]["dbh"] == 0.10
        first = data["sensors"][0]
        assert {"detection_probability", "expected_returns", "reliable_probability",
                "characterization_probability", "sensor_id"} <= set(first.keys())