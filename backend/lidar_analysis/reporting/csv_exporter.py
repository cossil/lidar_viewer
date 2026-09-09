"""CSV export for numerical simulation/sweep data (PRD sec 60; SCHEMAS sec 20-24).

Flattens a results dict (metrics, effective_ranges, distribution(( into summary rows. Sweep
results follow as per-row flattening of each sweep result. Detected point-cloud rows
(point_cloud.points( are appended when include_points is True.
"""

from __future__ import annotations

import csv
import os
from typing import Any, Iterable


def _rows_from_points(points: list[dict]) -> list[dict]:
    ordered: list[str] = [
        "trial_id", "x", "y", "z", "true_range", "measured_range", "range_error",
        "azimuth", "elevation", "incidence_angle", "detection_probability", "target_surface",
    ]
    out: list[dict] = []
    for p in points:
        row = {}
        for k in ordered:
            if k in p:
                row[k] = p[k]
        out.append(row)
    return out


def results_to_rows(results: dict, include_points: bool = True) -> list[dict]:
    rows: list[dict] = []
    metrics = results.get("metrics", {})
    summary: dict = {}
    for k in (
        "detection_probability", "reliable_probability", "characterization_probability",
        "expected_target_returns", "geometric_coverage", "target_angular_size",
        "beam_footprint", "incidence_angle", "range_uncertainty",
    ):
        if k in metrics:
            summary[k] = metrics[k]
    er = results.get("effective_ranges", {})
    for k in ("detection", "reliable", "characterization"):
        if k in er:
            summary["effective_range_" + k] = er[k]
    rows.append(summary)

    sweep = results.get("sweep", {})
    if sweep:
        swept_vals = sweep.get("values", [])
        for r in sweep.get("results", []):
            row: dict = {"sweep_type": sweep.get("type", ""), "sweep_parameter": sweep.get("parameter", "")}
            val_idx = r.get("parameter_value_idx")
            if val_idx is not None:
                if 0 <= val_idx < len(swept_vals):
                    row["sweep_value"] = swept_vals[val_idx]
            for k in (
                "detection_probability", "reliable_probability", "characterization_probability",
                "expected_target_returns", "geometric_coverage", "range_uncertainty",
            ):
                if k in r:
                    row[k] = r[k]
            if r.get("point_cloud"):
                row["count"] = len(r["point_cloud"])
            rows.append(row)

    if include_points:
        pts = results.get("point_cloud", {}).get("points", [])
        if pts:
            rows.append({})
            rows.extend(_rows_from_points(pts))
    return rows


def write_csv(rows: Iterable[dict], path: str, fieldnames: list[str] | None = None) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    rows = list(rows)
    if not rows:
        rows = [{}]
    keys: list[str] = list(fieldnames or [])
    if not keys:
        seen = set()
        for r in rows:
            for k in r:
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path