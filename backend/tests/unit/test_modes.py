"""Simulation modes tests (PRD section 54).

Covers the analytical (deterministic) and synthetic_point_cloud modes,
and verifies they share the same model components as Monte Carlo.
"""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from lidar_analysis.api.app import create_app
from lidar_analysis.geometry.rays import direction_from_angles
from lidar_analysis.geometry.targets import Cylinder
from lidar_analysis.physics.detection import AssumptionModel
from lidar_analysis.physics.measurement import MeasurementConfig, MeasurementModel
from lidar_analysis.scan.scanners import ScanPoint
from lidar_analysis.simulation.engine import SingleTrialEngine
from lidar_analysis.simulation.analytical import run_analytical
from lidar_analysis.simulation.pointcloud import generate_point_cloud
from lidar_analysis.simulation.monte_carlo import MonteCarloEngine


def _make_engine(seed: int = 42):
    target = Cylinder.from_dbh(1.0, [5, 0, 0], [0, 0, 1], 0.9)
    cfg = MeasurementConfig(bias=0.0, sigma=0.01)
    mm = MeasurementModel(range_config=cfg, angular_config=cfg)
    return SingleTrialEngine(
        target=target,
        detection_model=AssumptionModel(assumed_probability=1.0),
        measurement_model=mm,
        beam_divergence=0.003,
        rng=np.random.default_rng(seed),
    )


def _make_points(n: int = 5):
    pts = []
    for i in range(n):
        az = (i - n / 2) * 0.01
        pts.append(ScanPoint(
            horizontal_angle=az, vertical_angle=0.0,
            channel_index=0, time=0.0,
            direction=direction_from_angles(az, 0.0),
        ))
    return pts


class TestAnalyticalMode:
    def test_deterministic(self):
        engine = _make_engine()
        pts = _make_points()
        r1 = run_analytical(engine, pts, np.array([0, 0, 0.0]))
        r2 = run_analytical(engine, pts, np.array([0, 0, 0.0]))
        assert r1.expected_returns == pytest.approx(r2.expected_returns)
        assert r1.expected_detections == r2.expected_detections

    def test_matches_mc_mean(self):
        """Analytical expectation agrees with the Monte Carlo mean (shared engine)."""
        engine = _make_engine()
        pts = _make_points()
        sensor_pos = np.array([0, 0, 0.0])
        ar = run_analytical(engine, pts, sensor_pos)
        mc = MonteCarloEngine(engine, n_trials=30, seed=7)
        mr = mc.run(pts, sensor_pos)
        # deterministic P_d=1.0 target: expected_returns ~ mean detections
        assert abs(ar.expected_returns - mr.detection_count_stats.mean) < 0.5

    def test_coverage_in_result(self):
        engine = _make_engine()
        pts = _make_points()
        r = run_analytical(engine, pts, np.array([0, 0, 0.0]))
        assert 0.0 <= r.coverage <= 1.0


class TestPointCloudMode:
    def test_returns_detected_points(self):
        engine = _make_engine()
        pts = _make_points(8)
        sensor_pos = np.array([0, 0, 0.0])
        pc = generate_point_cloud(engine, pts, sensor_pos)
        assert pc.point_count > 0
        assert pc.point_count == engine.run(pts, sensor_pos).detections
        row = pc.points[0]
        assert len(row) == 3  # az, el, range

    def test_deterministic(self):
        engine = _make_engine()
        pts = _make_points()
        sensor_pos = np.array([0, 0, 0.0])
        pc1 = generate_point_cloud(engine, pts, sensor_pos)
        pc2 = generate_point_cloud(engine, pts, sensor_pos)
        assert pc1.points == pc2.points


@pytest.fixture()
def client():
    return TestClient(create_app())


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
        "sensor_pose": {"position": [0, 0, 1.5], "orientation": {"yaw": 0, "pitch": 0, "roll": 0}},
        "target": {
            "type": "cylinder",
            "position": [30, 0, 0.5],
            "orientation": [0, 0, 1],
            "diameter": 0.10,
            "reflectivity": 0.3,
        },
    }


def _sim(opts):
    base = {
        "scenario_id": "test-scenario-001",
        "mode": "monte_carlo",
        "duration": 0.01,
        "monte_carlo": {"enabled": True, "trials": 10, "random_seed": 42},
        "detection_model_id": None,
        "measurement_model": {"range_bias": 0.0, "range_sigma": 0.0002, "range_error_definition": "1sigma"},
    }
    base.update(opts)
    return base


class TestSimulationModesAPI:
    def _setup(self, client, sensor, scenario):
        client.post("/api/sensors", json=sensor)
        client.post("/api/scenarios", json=scenario)

    def test_analytical_mode(self, client, sample_sensor_data, sample_scenario_data):
        self._setup(client, sample_sensor_data, sample_scenario_data)
        r = client.post("/api/simulations", json=_sim({"mode": "analytical"}))
        assert r.status_code == 202
        sim_id = r.json()["simulation_id"]
        rr = client.get(f"/api/simulations/{sim_id}/results")
        assert rr.status_code == 200
        body = rr.json()
        assert body["mode"] == "analytical"
        assert "expected_returns" in body
        assert "coverage" in body

    def test_pointcloud_mode(self, client, sample_sensor_data, sample_scenario_data):
        self._setup(client, sample_sensor_data, sample_scenario_data)
        r = client.post("/api/simulations", json=_sim({"mode": "synthetic_point_cloud"}))
        assert r.status_code == 202
        sim_id = r.json()["simulation_id"]
        rr = client.get(f"/api/simulations/{sim_id}/results")
        assert rr.status_code == 200
        body = rr.json()
        assert body["mode"] == "synthetic_point_cloud"
        assert body["point_count"] > 0
        assert isinstance(body["points"], list)

    def test_invalid_mode_422(self, client, sample_sensor_data, sample_scenario_data):
        self._setup(client, sample_sensor_data, sample_scenario_data)
        r = client.post("/api/simulations", json=_sim({"mode": "bogus"}))
        assert r.status_code == 422