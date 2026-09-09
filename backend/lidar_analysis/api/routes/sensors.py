"""Sensor CRUD routes (PRD section 58).

GET    /api/sensors
POST   /api/sensors
GET    /api/sensors/{id}
PUT    /api/sensors/{id}
DELETE /api/sensors/{id}
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ...models.sensor import Sensor
from ..store import store

router = APIRouter()


@router.get("", response_model=List[dict])
def list_sensors():
    """List all sensors."""
    return [s.model_dump() for s in store.list_sensors()]


@router.post("", status_code=201)
def create_sensor(sensor: Sensor):
    """Create a new sensor."""
    sid = store.put_sensor(sensor)
    return {"sensor_id": sid, "status": "created"}


@router.get("/{sensor_id}")
def get_sensor(sensor_id: str):
    """Get a sensor by ID."""
    sensor = store.get_sensor(sensor_id)
    if sensor is None:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")
    return sensor.model_dump()


@router.get("/{sensor_id}/versions")
def list_sensor_versions(sensor_id: str):
    """List all immutable version snapshots for a sensor (Rule 9)."""
    versions = store.list_sensor_versions(sensor_id)
    return versions


@router.put("/{sensor_id}")
def update_sensor(sensor_id: str, sensor: Sensor):
    """Update a sensor, bumping its version and preserving the prior immutable snapshot (Rule 9)."""
    existing = store.get_sensor(sensor_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")
    # Preserve the current (old) version as an immutable snapshot before replacing it.
    store.snapshot_sensor(sensor_id)
    # Resolve the new version: use the submitted version if it differs, else bump the minor version.
    new_version = sensor.version if sensor.version != existing.version else _bump_minor(existing.version)
    sensor.version = new_version
    store.put_sensor(sensor)
    # Snapshot the new version too, so any version a simulation references is resolvable (Rule 9).
    store.snapshot_sensor(sensor_id)
    return {"sensor_id": sensor_id, "status": "updated", "version": new_version}


def _bump_minor(version: str) -> str:
    """Bump the minor version of a dotted version string (e.g. "1.0.0" -> "1.1.0")."""
    parts = version.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 and parts[0] else 1
        minor = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    except ValueError:
        major, minor = 1, 0
    return f"{major}.{minor + 1}.0"


@router.delete("/{sensor_id}")
def delete_sensor(sensor_id: str):
    """Delete a sensor."""
    if not store.delete_sensor(sensor_id):
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")
    return {"sensor_id": sensor_id, "status": "deleted"}