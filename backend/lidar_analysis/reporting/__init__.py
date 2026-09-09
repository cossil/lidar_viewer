"""Report generation (PRD section 60).

Exports: CSV, JSON, Markdown engineering reports.

Markdown report structure (PRD section 60):
1. Executive summary
2. Sensor information
3. Scenario
4. Target
5. Environmental assumptions
6. Mathematical model
7. Detection model
8. Simulation configuration
9. Results
10. Statistical analysis
11. Limitations
12. Assumptions
13. Provenance
14. Conclusions
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def export_json(data: Dict[str, Any], pretty: bool = True) -> str:
    """Export data as JSON string."""
    return json.dumps(data, indent=2 if pretty else None, default=str)


def export_csv(headers: List[str], rows: List[List[Any]]) -> str:
    """Export tabular data as CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()


def generate_markdown_report(
    title: str,
    sensor_info: Optional[Dict[str, Any]] = None,
    scenario_info: Optional[Dict[str, Any]] = None,
    target_info: Optional[Dict[str, Any]] = None,
    environment_info: Optional[Dict[str, Any]] = None,
    mathematical_model: Optional[str] = None,
    detection_model: Optional[Dict[str, Any]] = None,
    simulation_config: Optional[Dict[str, Any]] = None,
    results: Optional[Dict[str, Any]] = None,
    statistical_analysis: Optional[Dict[str, Any]] = None,
    limitations: Optional[List[str]] = None,
    assumptions: Optional[List[str]] = None,
    provenance: Optional[List[Dict[str, Any]]] = None,
    conclusions: Optional[str] = None,
) -> str:
    """Generate a Markdown engineering report (PRD section 60)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sections = []

    # Header
    sections.append(f"# {title}\n")
    sections.append(f"**Generated:** {now}\n")

    # 1. Executive summary
    sections.append("## 1. Executive Summary\n")
    if results:
        p_det = results.get("p_detected", "N/A")
        p_rel = results.get("p_reliable", "N/A")
        p_char = results.get("p_characterized", "N/A")
        sections.append(f"- Detection probability: {p_det:.3f}" if isinstance(p_det, float) else f"- Detection probability: {p_det}")
        sections.append(f"- Reliable detection probability: {p_rel:.3f}" if isinstance(p_rel, float) else f"- Reliable detection probability: {p_rel}")
        sections.append(f"- Characterization probability: {p_char:.3f}" if isinstance(p_char, float) else f"- Characterization probability: {p_char}")
    else:
        sections.append("No simulation results available.\n")
    sections.append("")

    # 2. Sensor information
    sections.append("## 2. Sensor Information\n")
    if sensor_info:
        for k, v in sensor_info.items():
            sections.append(f"- **{k}:** {v}")
    else:
        sections.append("No sensor information.\n")
    sections.append("")

    # 3. Scenario
    sections.append("## 3. Scenario\n")
    if scenario_info:
        for k, v in scenario_info.items():
            sections.append(f"- **{k}:** {v}")
    else:
        sections.append("No scenario information.\n")
    sections.append("")

    # 4. Target
    sections.append("## 4. Target\n")
    if target_info:
        for k, v in target_info.items():
            sections.append(f"- **{k}:** {v}")
    else:
        sections.append("No target information.\n")
    sections.append("")

    # 5. Environmental assumptions
    sections.append("## 5. Environmental Assumptions\n")
    if environment_info:
        for k, v in environment_info.items():
            sections.append(f"- **{k}:** {v}")
    else:
        sections.append("Clear atmosphere assumed.\n")
    sections.append("")

    # 6. Mathematical model
    sections.append("## 6. Mathematical Model\n")
    if mathematical_model:
        sections.append(mathematical_model)
    else:
        sections.append("Standard LiDAR range equation.\n")
    sections.append("")

    # 7. Detection model
    sections.append("## 7. Detection Model\n")
    if detection_model:
        for k, v in detection_model.items():
            sections.append(f"- **{k}:** {v}")
    else:
        sections.append("No detection model information.\n")
    sections.append("")

    # 8. Simulation configuration
    sections.append("## 8. Simulation Configuration\n")
    if simulation_config:
        for k, v in simulation_config.items():
            sections.append(f"- **{k}:** {v}")
    else:
        sections.append("No simulation configuration.\n")
    sections.append("")

    # 9. Results
    sections.append("## 9. Results\n")
    if results:
        for k, v in results.items():
            if isinstance(v, dict):
                sections.append(f"### {k}\n")
                for kk, vv in v.items():
                    sections.append(f"- **{kk}:** {vv}")
            else:
                sections.append(f"- **{k}:** {v}")
    else:
        sections.append("No results.\n")
    sections.append("")

    # 10. Statistical analysis
    sections.append("## 10. Statistical Analysis\n")
    if statistical_analysis:
        for k, v in statistical_analysis.items():
            sections.append(f"- **{k}:** {v}")
    else:
        sections.append("No statistical analysis.\n")
    sections.append("")

    # 11. Limitations
    sections.append("## 11. Limitations\n")
    if limitations:
        for lim in limitations:
            sections.append(f"- {lim}")
    else:
        sections.append("No limitations documented.\n")
    sections.append("")

    # 12. Assumptions
    sections.append("## 12. Assumptions\n")
    if assumptions:
        for a in assumptions:
            sections.append(f"- {a}")
    else:
        sections.append("No assumptions documented.\n")
    sections.append("")

    # 13. Provenance
    sections.append("## 13. Provenance\n")
    if provenance:
        for p in provenance:
            sections.append(f"- {p}")
    else:
        sections.append("No provenance information.\n")
    sections.append("")

    # 14. Conclusions
    sections.append("## 14. Conclusions\n")
    if conclusions:
        sections.append(conclusions)
    else:
        sections.append("No conclusions.\n")

    return "\n".join(sections)


def distance_sweep_to_csv(sweep_data: Dict[str, Any]) -> str:
    """Export distance sweep results as CSV."""
    headers = ["distance", "p_detected", "p_reliable", "p_characterized", "expected_returns"]
    rows = []
    for p in sweep_data.get("distances", []):
        rows.append([
            p.get("distance", ""),
            p.get("p_detected", ""),
            p.get("p_reliable", ""),
            p.get("p_characterized", ""),
            p.get("expected_returns", ""),
        ])
    return export_csv(headers, rows)


def comparison_to_csv(comparison_data: Dict[str, Any]) -> str:
    """Export sensor comparison results as CSV."""
    headers = ["sensor_id", "p_detected", "p_reliable", "p_characterized", "expected_returns_mean"]
    rows = []
    for entry in comparison_data.get("comparison", []):
        rows.append([
            entry.get("sensor_id", ""),
            entry.get("p_detected", ""),
            entry.get("p_reliable", ""),
            entry.get("p_characterized", ""),
            entry.get("expected_returns_mean", ""),
        ])
    return export_csv(headers, rows)