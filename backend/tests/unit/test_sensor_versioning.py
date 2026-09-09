"""Tests for sensor versioning (Rule 9), seed retention (Rule 10),
assumption registry ( PRD 61 ), and the insufficient-data guard ( section 27 ).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lidar_analysis.api.app import create_app
from lidar_analysis.api.store import store
from lidar_analysis.api.assumptions import ASSUMPTION_REGISTRY


def _clear_store():
    store._sensors.clear()
    store._sensor_versions.clear()
    store._scenarios.clear()
    store._simulations.clear()
    store._jobs.clear()


@pytest.fixture()
def client():
    _clear_store()
    ASSUMPTION_REGISTRY._assumptions.clear()
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def sample_sensor_data():
    return {
        "sensor_id": "hesai-qt64",
        "sensor_type": "mechanical_spinning",
        "manufacturer": "Hesai",
        "model": "QT64",
        "version": "1.0.0",
        "wavelength": {"value": 905, "unit": "nm", "origin": "SOURCE", "status": "known"},
        "range": {"maximum": {"value": 200, "unit": "m", "origin": "SOURCE", "status": "known"}},
        "accuracy": {"range": {"value": 0.02, "unit": "m", "origin": "SOURCE", "status": "known"}},
        "beam": {"horizontal_divergence": {"value": 0.003, "unit": "rad", "origin": "SOURCE", "status": "known"}},
        "scan": {
            "type": "mechanical_spinning",
            "point_rate": {"value": 600000, "unit": "Hz", "origin": "SOURCE", "status": "known"},
            "rotation_frequency": {"value": 10, "unit": "Hz", "origin": "SOURCE", "status": "known"},
            "frame_rate": {"value": 10, "unit": "Hz", "origin": "SOURCE", "status": "known"},
        },
        "validation": {"status": "validated"},
    }


@pytest.fixture()
def sample_scenario_data():
    return {
        "scenario_id": "test-scenario-001",
        "sensor_id": "hesai-qt64",
        "environment": {"atmosphere": "clear"},
        "sensor_pose": {"position": [0, 0, 1.5], "orientation": {"yaw": 0, "pitch":  0, "roll":  0}},
        "target": {
            "type": "cylinder",
            "position": [30, 0, 0.5],
            "orientation": [0, 0, 1],
            "diameter": 0.10,
            "reflectivity": 0.3,
        },
    }


def _sim(opts=None):
    base = {
        "scenario_id": "test-scenario-001",
        "mode": "monte_carlo",
        "duration": 0.01,
        "monte_carlo": {"enabled": True, "trials": 10, "random_seed": 42},
        "detection_model_id": None,
        "measurement_model": {"range_bias": 0.0, "range_sigma":  0.0002, "range_error_definition": "1sigma"},
    }
    if opts:
        base.update(opts)
    return base


class TestSensorVersioning:

    def test_put_bumps_version_and_keeps_snapshot(self, client, sample_sensor_data):
        client.post("/api/sensors", json=sample_sensor_data)
        sample_sensor_data["version"] = "1.1.0"
        resp = client.put("/api/sensors/hesai-qt64", json=sample_sensor_data)
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.1.0"
        latest = store.get_sensor("hesai-qt64")
        assert latest.version == "1.1.0"
        assert store.get_sensor_version("hesai-qt64", "1.0.0")  is not None
        assert store.get_sensor_version("hesai-qt64", "1.1.0")  is not None
        versions = client.get("/api/sensors/hesai-qt64/versions").json()
        assert {v["version"] for v in versions} == {"1.0.0", "1.1.0"}

    def test_put_without_version_bumps_minor(self, client, sample_sensor_data):
        client.post("/api/sensors", json=sample_sensor_data)
        resp = client.put("/api/sensors/hesai-qt64", json=sample_sensor_data)
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.1.0"
        assert store.get_sensor_version("hesai-qt64", "1.0.0")  is not None

    def test_versions_endpoint_lists_both(self, client, sample_sensor_data):
        client.post("/api/sensors", json=sample_sensor_data)
        sample_sensor_data["version"] = "2.0.0"
        client.put("/api/sensors/hesai-qt64", json=sample_sensor_data)
        versions = client.get("/api/sensors/hesai-qt64/versions").json()
        assert len(versions) == 2
        assert {v["version"] for v in versions} == {"1.0.0", "2.0.0"}


class TestSimulationPinsSensorVersionAndSeed:

    def _setup(self, client, sensor, scenario):
        client.post("/api/sensors", json=sensor)
        client.post("/api/scenarios", json=scenario)

    def test_monte_carlo_records_metadata(self, client, sample_sensor_data, sample_scenario_data):
        self._setup(client, sample_sensor_data, sample_scenario_data)
        sim_id = client.post("/api/simulations", json=_sim()).json()["simulation_id"]
        result = client.get(f"/api/simulations/{sim_id}/results").json()
        assert result["sensor_version"] == "1.0.0"
        assert result["seed"] == 42
        assert result["assumptions"]
        for aid in result["assumptions"]:
            assert ASSUMPTION_REGISTRY.get(aid) is not None

    def test_version_pinned_across_update(self, client, sample_sensor_data, sample_scenario_data):
        self._setup(client, sample_sensor_data, sample_scenario_data)
        first = client.post("/api/simulations", json=_sim()).json()["simulation_id"]
        sample_sensor_data["version"] = "1.1.0"
        client.put("/api/sensors/hesai-qt64", json=sample_sensor_data)
        second = client.post("/api/simulations", json=_sim()).json()["simulation_id"]
        r1 = client.get(f"/api/simulations/{first}/results").json()
        r2 = client.get(f"/api/simulations/{second}/results").json()
        assert r1["sensor_version"] == "1.0.0"
        assert r2["sensor_version"] == "1.1.0"

    def test_analytical_records_seed_zero(self, client, sample_sensor_data, sample_scenario_data):
        self._setup(client, sample_sensor_data, sample_scenario_data)
        sim_id = client.post("/api/simulations", json=_sim({"mode": "analytical"})).json()["simulation_id"]
        result = client.get(f"/api/simulations/{sim_id}/results").json()
        assert result["mode"] == "analytical"
        assert result["seed"] == 0
        assert result["sensor_version"] == "1.0.0"
        assert result["assumptions"]


class TestAssumptionRegistry:

    def test_register_get_list_roundtrip(self):
        from lidar_analysis.api.assumptions import AssumptionRegistry
        reg = AssumptionRegistry()
        aid = reg.register({"description": "manual assumption"})
        assert aid.startswith("assumption_")
        assert reg.get(aid)["description"] == "manual assumption"
        descs = {a["description"] for a in reg.list()}
        assert "manual assumption" in descs

    def test_record_default_assumptions(self):
        from lidar_analysis.api.assumptions import record_default_assumptions
        ids = record_default_assumptions("sim_test")
        assert len(ids) == 4
        for aid in ids:
            assert ASSUMPTION_REGISTRY.get(aid)["simulation_id"] == "sim_test"


class TestInsufficientDataResponse:

    def test_unknown_max_range_returns_409(self, client, sample_sensor_data, sample_scenario_data):
        sample_sensor_data["range"]["maximum"] = {"value": None, "unit": "m", "origin": "SOURCE", "status": "unknown"}
        client.post("/api/sensors", json=sample_sensor_data)
        client.post("/api/scenarios", json=sample_scenario_data)
        resp = client.post("/api/simulations", json=_sim())
        assert resp.status_code == 409
        body = resp.json()
        assert body["status"] == "insufficient_data"
        assert "range.maximum" in body["missing_parameters"]
        assert "message" in body