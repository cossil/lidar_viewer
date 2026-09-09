"""Common pytest fixtures for unit tests."""

import pytest


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
