"""JSON file persistence backend (PRD §55-57; SCHEMAS §33-36, Decision D008).

Persists domain objects to structured JSON files on disk:
  data/sensors/<sensor_id>.v<version>.json + <sensor_id>.latest
  data/scenarios/<scenario_id>.json
  data/simulations/<simulation_id>.json
  data/reports/<report_id>.json

Supports soft deletion via .deleted sidecar files and full roundtrip loading.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.sensor import Sensor
from ..models.scenario import Scenario


def get_default_data_dir() -> Path:
    """Resolve data directory relative to repository root or environment."""
    env_dir = os.environ.get("LIDAR_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    # Default: 4 levels up from this file or search upward for 'data'
    cur = Path(__file__).resolve().parent
    for p in [cur.parent.parent.parent / "data", cur.parent.parent / "data", Path("data")]:
        if p.exists() and p.is_dir():
            return p
    return Path("data")


class DiskPersistence:
    """Handles disk serialization and deserialization for the store."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else get_default_data_dir()
        self.sensors_dir = self.base_dir / "sensors"
        self.scenarios_dir = self.base_dir / "scenarios"
        self.simulations_dir = self.base_dir / "simulations"
        self.reports_dir = self.base_dir / "reports"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in [self.sensors_dir, self.scenarios_dir, self.simulations_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # ------------------ Sensors ------------------

    def save_sensor(self, sensor: Sensor) -> None:
        """Write sensor to disk: <sensor_id>.v<version>.json and update <sensor_id>.latest."""
        self._ensure_dirs()
        sid = sensor.sensor_id
        version = sensor.version
        file_path = self.sensors_dir / f"{sid}.v{version}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sensor.model_dump_json(indent=2))

        latest_path = self.sensors_dir / f"{sid}.latest"
        with open(latest_path, "w", encoding="utf-8") as f:
            f.write(version)

        # Clear deleted marker if it was soft-deleted earlier
        deleted_marker = self.sensors_dir / f"{sid}.deleted"
        if deleted_marker.exists():
            deleted_marker.unlink()

    def soft_delete_sensor(self, sensor_id: str) -> None:
        """Mark sensor as deleted via .deleted sidecar file."""
        self._ensure_dirs()
        marker = self.sensors_dir / f"{sensor_id}.deleted"
        marker.write_text("deleted", encoding="utf-8")

    def load_sensors(self) -> Tuple[Dict[str, Sensor], Dict[str, Sensor]]:
        """Load all sensor versions and active latest sensors from disk."""
        active_sensors: Dict[str, Sensor] = {}
        sensor_versions: Dict[str, Sensor] = {}

        if not self.sensors_dir.exists():
            return active_sensors, sensor_versions

        # Find all .v*.json files
        for p in self.sensors_dir.glob("*.v*.json"):
            try:
                content = p.read_text(encoding="utf-8")
                sensor_dict = json.loads(content)
                sensor = Sensor.model_validate(sensor_dict)
                key = f"{sensor.sensor_id}@{sensor.version}"
                sensor_versions[key] = sensor
            except Exception:
                continue

        # For active sensors, inspect .latest pointers
        for latest_p in self.sensors_dir.glob("*.latest"):
            sid = latest_p.stem
            deleted_marker = self.sensors_dir / f"{sid}.deleted"
            if deleted_marker.exists():
                continue
            version = latest_p.read_text(encoding="utf-8").strip()
            key = f"{sid}@{version}"
            if key in sensor_versions:
                active_sensors[sid] = sensor_versions[key]

        return active_sensors, sensor_versions

    # ------------------ Scenarios ------------------

    def save_scenario(self, scenario: Scenario) -> None:
        """Write scenario to disk: <scenario_id>.json."""
        self._ensure_dirs()
        sid = scenario.scenario_id
        path = self.scenarios_dir / f"{sid}.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(scenario.model_dump_json(indent=2))

        deleted_marker = self.scenarios_dir / f"{sid}.deleted"
        if deleted_marker.exists():
            deleted_marker.unlink()

    def soft_delete_scenario(self, scenario_id: str) -> None:
        """Mark scenario as deleted via .deleted sidecar file."""
        self._ensure_dirs()
        marker = self.scenarios_dir / f"{scenario_id}.deleted"
        marker.write_text("deleted", encoding="utf-8")

    def load_scenarios(self) -> Dict[str, Scenario]:
        """Load active scenarios from disk."""
        scenarios: Dict[str, Scenario] = {}
        if not self.scenarios_dir.exists():
            return scenarios

        for p in self.scenarios_dir.glob("*.json"):
            sid = p.stem
            deleted_marker = self.scenarios_dir / f"{sid}.deleted"
            if deleted_marker.exists():
                continue
            try:
                content = p.read_text(encoding="utf-8")
                sc = Scenario.model_validate(json.loads(content))
                scenarios[sid] = sc
            except Exception:
                continue
        return scenarios

    # ------------------ Simulations / Jobs ------------------

    def save_job(self, job_dict: dict) -> None:
        """Write simulation job & results to disk: <simulation_id>.json."""
        self._ensure_dirs()
        sim_id = job_dict.get("simulation_id")
        if not sim_id:
            return
        path = self.simulations_dir / f"{sim_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(job_dict, f, indent=2)

    def load_jobs(self) -> Dict[str, dict]:
        """Load simulations and results from disk."""
        jobs: Dict[str, dict] = {}
        if not self.simulations_dir.exists():
            return jobs

        for p in self.simulations_dir.glob("*.json"):
            sim_id = p.stem
            try:
                jobs[sim_id] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
        return jobs

    # ------------------ Reports ------------------

    def save_report(self, report_id: str, report_data: dict) -> None:
        """Write report to disk: <report_id>.json."""
        self._ensure_dirs()
        path = self.reports_dir / f"{report_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

    def load_reports(self) -> Dict[str, dict]:
        """Load reports from disk."""
        reports: Dict[str, dict] = {}
        if not self.reports_dir.exists():
            return reports

        for p in self.reports_dir.glob("*.json"):
            rid = p.stem
            try:
                reports[rid] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
        return reports
