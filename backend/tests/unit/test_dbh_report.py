"""Integration tests for DBH sweep and Report APIs.

Tests:
  - dbh-sweep returns 200 with points/analysis_id
  - dbh-sweep unknown scenario returns 404
  - report create returns report_id/status/format, then GET returns same body (markdown and json
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from lidar_analysis.api.app import create_app
from lidar_analysis.api.store import store


@pytest.fixture()
def client():
    store._sensors.clear()
    store._scenarios.clear()
    store._simulations.clear()
    store._jobs.clear()
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def sample_sensor(client):
    sensor = {
        "sensor_id": "hesai-qt64",
        "sensor_type": "mechanical_spinning",
        "manufacturer": "Hesai",
        "model": "QT64",
        "version": "1.0.0",
        "wavelength": {"value": 905, "unit": "nm", "origin": "SOURCE", "status": "known"},
        "range": {"maximum": {"value": 200, "unit": "m", "origin": "SOURCE", "status": "known"}},
        "accuracy": {"range": {"value":0.02, "unit": "m", "origin": "SOURCE", "status": "known"}},
        "beam": {"horizontal_divergence": {"value": 0.003, "unit": "rad", "origin": "SOURCE", "status": "known"}},
        "scan": {"type": "mechanical_spinning", "point_rate": {"value": 600000, "unit": "Hz", "origin": "SOURCE", "status": "known"}, "rotation_frequency": {"value": 10, "unit": "Hz", "origin": "SOURCE", "status": "known"}, "frame_rate": {"value":10, "unit": "Hz", "origin": "SOURCE", "status": "known"}},
        "validation": {"status": "validated"},
    }
    resp = client.post("/api/sensors", json=sensor)
    assert resp.status_code == 201


@pytest.fixture()
def sample_scenario(client, sample_sensor):
    scenario = {
        "scenario_id": "test-scenario-001",
        "sensor_id": "hesai-qt64",
        "environment": {"atmosphere": "clear"},
        "sensor_pose": {"position": [0,0,1.5], "orientation": {"yaw":0, "pitch":0, "roll":0}},
        "target": {"type": "cylinder", "position": [30,0,0.5], "orientation": [0,0,1], "diameter": 0.10, "reflectivity": 0.3},
    }
    resp = client.post("/api/scenarios", json=scenario)
    assert resp.status_code == 201


class TestDbhSweep:
    def test_dbh_sweep_returns_points(self, client, sample_scenario):
        resp = client.post("/api/analysis/dbh-sweep", json={
            "scenario_id": "test-scenario-001",
            "dbh": {"start": 0.05, "end": 0.15, "step":0.05},
            "distance":30,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["analysis_id"].startswith("dbhsweep_")
        assert len(data["points"]) > 0
        assert "dbh" in data["points"][0]
        assert "p_detected" in data["points"][0]

    def test_dbh_sweep_scenario_not_found(self, client):
        resp = client.post("/api/analysis/dbh-sweep", json={
            "scenario_id": "nonexistent",
            "dbh": {"start": 0.05, "end": 0.15, "step":0.05},
        })
        assert resp.status_code == 404


class TestReports:
    def _run_simulation(self, client):
        resp = client.post("/api/simulations", json={
            "scenario_id": "test-scenario-001",
            "mode": "monte_carlo",
            "duration":0.01,
            "monte_carlo": {"enabled":True, "trials":10, "random_seed":42},
            "detection_model_id":None,
            "measurement_model": {"range_bias":0.0, "range_sigma":0.0002, "range_error_definition":"1sigma"},
        })
        assert resp.status_code == 202
        return resp.json()["simulation_id"]

    def test_report_markdown(self, client, sample_scenario):
        sim_id = self._run_simulation(client)
        resp = client.post("/api/reports", json={"simulation_id": sim_id, "format": "markdown"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"].startswith("report_")
        assert data["status"] == "completed"
        assert data["format"] == "markdown"
        g = client.get(f"/api/reports/{data['report_id']}")
        assert g.status_code == 200
        gd = g.json()
        assert gd["format"] == "markdown"
        assert "body" in gd
        assert "Executive Summary" in gd["body"]

    def test_report_json(self, client, sample_scenario):
        sim_id = self._run_simulation(client)
        resp = client.post("/api/reports", json={"simulation_id": sim_id, "format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "json"
        g = client.get(f"/api/reports/{data['report_id']}")
        assert g.status_code == 200
        gd = g.json()
        assert json.loads(gd["body"])

    def test_report_not_found(self, client):
        resp = client.get("/api/reports/report_nope")
        assert resp.status_code == 404