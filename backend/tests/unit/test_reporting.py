"""Reporting tests (PRD section 60).

Tests:
  - JSON export
  - CSV export
  - Markdown report structure (14 sections)
  - Distance sweep CSV export
  - Comparison CSV export
"""

from __future__ import annotations

import csv
import io
import json

import pytest

from lidar_analysis.reporting import (
    comparison_to_csv,
    distance_sweep_to_csv,
    export_csv,
    export_json,
    generate_markdown_report,
)


class TestJSONExport:
    def test_pretty(self):
        data = {"key": "value", "nested": {"a": 1}}
        result = export_json(data)
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["nested"]["a"] == 1

    def test_compact(self):
        data = {"key": "value"}
        result = export_json(data, pretty=False)
        assert "\n" not in result


class TestCSVExport:
    def test_basic(self):
        result = export_csv(["name", "value"], [["foo", 1], ["bar", 2]])
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert rows[0] == ["name", "value"]
        assert rows[1] == ["foo", "1"]
        assert rows[2] == ["bar", "2"]

    def test_empty(self):
        result = export_csv(["a", "b"], [])
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1  # header only


class TestMarkdownReport:
    def test_all_sections_present(self):
        report = generate_markdown_report(
            title="Test Report",
            sensor_info={"model": "Hesai QT64"},
            results={"p_detected": 0.95, "p_reliable": 0.8},
            limitations=["Single target only"],
            assumptions=["Clear atmosphere"],
        )
        for section_num in range(1, 15):
            assert f"## {section_num}." in report
        assert "# Test Report" in report

    def test_results_in_report(self):
        report = generate_markdown_report(
            title="Test",
            results={"p_detected": 0.95},
        )
        assert "0.950" in report

    def test_minimal_report(self):
        report = generate_markdown_report(title="Minimal")
        assert "# Minimal" in report
        assert "## 1. Executive Summary" in report
        assert "## 14. Conclusions" in report


class TestDistanceSweepCSV:
    def test_export(self):
        data = {
            "distances": [
                {"distance": 10, "p_detected": 1.0, "p_reliable": 0.9, "p_characterized": 0.8, "expected_returns": 5.0},
                {"distance": 20, "p_detected": 0.8, "p_reliable": 0.5, "p_characterized": 0.3, "expected_returns": 2.5},
            ]
        }
        csv_str = distance_sweep_to_csv(data)
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 3  # header + 2 rows
        assert rows[0] == ["distance", "p_detected", "p_reliable", "p_characterized", "expected_returns"]


class TestComparisonCSV:
    def test_export(self):
        data = {
            "comparison": [
                {"sensor_id": "A", "p_detected": 0.9, "p_reliable": 0.8, "p_characterized": 0.7, "expected_returns_mean": 5.0},
            ]
        }
        csv_str = comparison_to_csv(data)
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[1][0] == "A"