"""Tests for disk persistence, detection model registry, error envelopes, and cancellation."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from lidar_analysis.api.app import create_app
from lidar_analysis.api.detection_registry import detection_registry
from lidar_analysis.api.errors import ApiError
from lidar_analysis.api.persistence import DiskPersistence
from lidar_analysis.api.store import Store, store
from lidar_analysis.models.sensor import Sensor


@pytest.fixture()
def temp_persistence(tmp_path):
    return DiskPersistence(base_dir=tmp_path / "data")


def test_persistence_roundtrip_and_versioning(temp_persistence, sample_sensor_data):
    custom_store = Store(persistence=temp_persistence)
    sensor = Sensor.model_validate(sample_sensor_data)
    sid = custom_store.put_sensor(sensor)
    assert sid == "hesai-qt64"

    # Verify disk files
    v_file = temp_persistence.sensors_dir / f"{sid}.v1.0.0.json"
    latest_file = temp_persistence.sensors_dir / f"{sid}.latest"
    assert v_file.exists()
    assert latest_file.exists()
    assert latest_file.read_text(encoding="utf-8").strip() == "1.0.0"

    # Create fresh store from disk
    restored_store = Store(persistence=temp_persistence)
    restored_sensor = restored_store.get_sensor(sid)
    assert restored_sensor is not None
    assert restored_sensor.sensor_id == sid
    assert restored_sensor.version == "1.0.0"
    assert restored_store.get_sensor_version(sid, "1.0.0") is not None


def test_soft_delete_preserves_disk_file(temp_persistence, sample_sensor_data):
    custom_store = Store(persistence=temp_persistence)
    sensor = Sensor.model_validate(sample_sensor_data)
    custom_store.put_sensor(sensor)

    # Soft delete
    custom_store.delete_sensor("hesai-qt64")
    assert custom_store.get_sensor("hesai-qt64") is None

    # Disk file is preserved, sidecar .deleted exists
    v_file = temp_persistence.sensors_dir / "hesai-qt64.v1.0.0.json"
    deleted_marker = temp_persistence.sensors_dir / "hesai-qt64.deleted"
    assert v_file.exists()
    assert deleted_marker.exists()


def test_detection_model_registry_resolution(sample_sensor_data):
    sensor = Sensor.model_validate(sample_sensor_data)
    models = detection_registry.list_models()
    assert len(models) >= 4
    model_ids = [m["model_id"] for m in models]
    assert "datasheet_envelope" in model_ids
    assert "analytical_physics" in model_ids

    # Resolve valid
    m1 = detection_registry.resolve("datasheet_envelope", sensor)
    assert m1 is not None

    m2 = detection_registry.resolve("analytical_physics", sensor)
    assert m2 is not None

    # Resolve invalid raises ApiError
    with pytest.raises(ApiError) as exc_info:
        detection_registry.resolve("non_existent_model_id", sensor)
    assert exc_info.value.code == "INVALID_DETECTION_MODEL"
    assert exc_info.value.status_code == 422


def test_error_envelope_format():
    app = create_app()
    client = TestClient(app)

    # 404 test
    resp = client.get("/api/sensors/sensor_never_exists_123")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "UNKNOWN_SENSOR"
    assert "not found" in data["error"]["message"].lower()

    # 422 validation test
    resp = client.post("/api/sensors", json={"invalid": "payload"})
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] in ("INVALID_PARAMETER", "MISSING_PARAMETER")


def test_simulation_cancellation(sample_sensor_data, sample_scenario_data):
    app = create_app()
    client = TestClient(app)
    client.post("/api/sensors", json=sample_sensor_data)
    client.post("/api/scenarios", json=sample_scenario_data)

    create_resp = client.post("/api/simulations", json={
        "scenario_id": "test-scenario-001",
        "mode": "monte_carlo",
        "duration": 0.01,
        "monte_carlo": {"enabled": True, "trials": 10, "random_seed": 42},
    })
    assert create_resp.status_code == 202
    sim_id = create_resp.json()["simulation_id"]

    cancel_resp = client.post(f"/api/simulations/{sim_id}/cancel")
    assert cancel_resp.status_code == 200
    assert "simulation_id" in cancel_resp.json()
