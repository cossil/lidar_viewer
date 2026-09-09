"""Unit tests for the datasheet ingestion and validation package."""

import pytest

from lidar_analysis.ingestion import EXTRACTIONS
from lidar_analysis.ingestion.datasheet_ingester import ingest_datasheet


@pytest.fixture(autouse=True)
def _clear_extractions():
    EXTRACTIONS.clear()
    yield
    EXTRACTIONS.clear()


def test_ingest_json_partial():
    data = {
        "manufacturer": "Acme",
        "model": "XL-100",
        "version": "1.0",
        "range": {"maximum": {"value": 70, "unit": "m"}},
        "validation_status": "unvalidated",
    }
    result = ingest_datasheet(data, "sensor.json", "application/json")
    assert result["status"] == "completed"
    assert result["extraction_id"].startswith("ext_")
    candidate = result["sensor_candidate"]
    assert candidate["manufacturer"] == "Acme"
    assert candidate["model"] == "XL-100"
    assert candidate["range"]["maximum"]["value"] == 70
    assert candidate["range"]["maximum"]["unit"] == "m"
    warn = result["warnings"]
    assert any("Beam divergence" in w for w in warn)
    assert result["extraction_id"] in EXTRACTIONS


def test_never_fabricates_unknown_value():
    data = {
        "manufacturer": "Acme",
        "range": {"maximum": {"value": None}},
        "beam": {"horizontal_divergence": {"value": None, "status": "unknown"}},
    }
    result = ingest_datasheet(data, "sensor.json", "application/json")
    candidate = result["sensor_candidate"]
    warn = result["warnings"]
    assert candidate["manufacturer"] == "Acme"
    assert "range" not in candidate
    assert "beam" not in candidate
    assert any("Maximum range" in w for w in warn)
    assert any("Beam divergence" in w for w in warn)


def test_validate_marks_validated():
    from lidar_analysis.ingestion.datasheet_validator import validate_datasheet

    ingested = ingest_datasheet(
        {"manufacturer": "Acme", "model": "M1"}, "s.json", "application/json"
    )
    extraction_id = ingested["extraction_id"]
    valid = {
        "range.maximum": {"value": 70, "unit": "m"},
        "scan.point_rate": {"value": 100000, "unit": "Hz"},
    }
    resp = validate_datasheet(extraction_id, valid)
    assert resp["validation_status"] == "validated"
    assert resp["sensor_id"]
    assert resp["version"]


def test_validate_needs_review_empty():
    from lidar_analysis.ingestion.datasheet_validator import validate_datasheet

    ingested = ingest_datasheet(
        {"manufacturer": "Acme", "model": "M1"}, "s.json", "application/json"
    )
    resp = validate_datasheet(ingested["extraction_id"], {})
    assert resp["validation_status"] == "needs_review"


def test_ingest_pdf_text_lines():
    text = "Maximum Range: 70 m\nPoint Rate:  100000 Hz"
    result = ingest_datasheet(text, "sensor.pdf", "application/pdf")
    candidate = result["sensor_candidate"]
    assert candidate["range"]["maximum"]["value"] == 70.0
    assert candidate["scan"]["point_rate"]["value"] == 100000.0


def test_sensor_reconstruction_warning():
    result = ingest_datasheet({"manufacturer": "Acme"}, "s.json", "application/json")
    warn = result["warnings"]
    assert any("manual completion" in w for w in warn)


def test_validate_unknown_id_raises():
    from lidar_analysis.ingestion.datasheet_validator import validate_datasheet

    with pytest.raises((KeyError, ValueError)):
        validate_datasheet("ext_deadbeef", {"a": {"value": 1, "unit": "m"}})