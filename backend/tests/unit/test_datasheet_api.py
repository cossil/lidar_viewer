"""Tests for the Datasheet Extraction and Validation API routes.

Covers SCHEMAS sections 14-15:
  - POST /api/datasheets/extract (JSON and text/pdf extraction)
  - POST /api/datasheets/{extraction_id}/validate
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lidar_analysis.api.app import create_app
from lidar_analysis.ingestion.datasheet_validator import clear_extractions, validate_datasheet


@pytest.fixture()
def client():
    clear_extractions()
    app = create_app()
    with TestClient(app) as c:
        yield c
    clear_extractions()


def test_extract_json_partial(client):
    payload = {
        "filename": "sensor.json",
        "content_type": "application/json",
        "data": {
            "manufacturer": "Luminar",
            "model": "Iris",
            "range": {"maximum": {"value": 70, "unit": "m"}},
        },
    }
    resp = client.post("/api/datasheets/extract", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["extraction_id"].startswith("ext_")
    assert body["status"] == "completed"
    candidate = body["sensor_candidate"]
    if isinstance(candidate, dict):
        assert candidate["range"]["maximum"]["value"] == 70
        assert candidate["manufacturer"] == "Luminar"
    warnings = " ".join(body["warnings"]).lower()
    assert "sensor id" in warnings


def test_extract_text_lines(client):
    payload = {
        "filename": "sensor.pdf",
        "content_type": "application/pdf",
        "data": {"text": "Maximum Range: 70 m\nPoint Rate: 100000 Hz"},
    }
    resp = client.post("/api/datasheets/extract", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    candidate = body["sensor_candidate"]
    if isinstance(candidate, dict):
        assert candidate["range"]["maximum"]["value"] == 70.0
        assert candidate["scan"]["point_rate"]["value"] == 100000.0


def test_validate_marks_validated(client):
    extract = client.post(
        "/api/datasheets/extract",
        json={
            "filename": "s.json",
            "content_type": "application/json",
            "data": {"sensor_id": "lidar-x1", "version": "2.1"},
        },
    )
    extraction_id = extract.json()["extraction_id"]
    resp = client.post(
        f"/api/datasheets/{extraction_id}/validate",
        json={"validated_parameters": {"range.maximum": {"value": 70, "unit": "m"}}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["validation_status"] == "validated"
    assert body["version"]
    assert body["sensor_id"] == "lidar-x1"


def test_validate_empty_needs_review(client):
    extract = client.post(
        "/api/datasheets/extract",
        json={
            "filename": "s.json",
            "content_type": "application/json",
            "data": {"sensor_id": "lidar-x2"},
        },
    )
    extraction_id = extract.json()["extraction_id"]
    resp = client.post(
        f"/api/datasheets/{extraction_id}/validate",
        json={"validated_parameters": {}},
    )
    assert resp.status_code == 200
    assert resp.json()["validation_status"] == "needs_review"


def test_validate_unknown_extraction_404(client):
    resp = client.post(
        "/api/datasheets/ext_doesnotexist/validate",
        json={"validated_parameters": {"range.maximum": {"value": 70}}},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_routes_registered():
    from lidar_analysis.api.routes import datasheets

    paths = {getattr(r, "path", None) for r in datasheets.router.routes}
    assert "/extract" in paths
    assert "/{extraction_id}/validate" in paths