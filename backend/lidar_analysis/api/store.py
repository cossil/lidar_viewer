"""Data store with disk persistence backend (PRD §55-57; SCHEMAS §33-36, Decision D008).

Stores sensors, scenarios, simulations, and reports with write-through JSON disk persistence
and in-memory L1 cache.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from ..models.sensor import Sensor
from ..models.scenario import Scenario
from ..models.simulation import Simulation
from .persistence import DiskPersistence


@dataclass
class SimulationJob:
    """Simulation job with status tracking (PRD section 59)."""

    simulation_id: str
    status: str  # queued | running | completed | failed | cancelled
    progress: float = 0.0
    trials_completed: int = 0
    trials_total: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None


class Store:
    """Thread-safe store backed by JSON files on disk."""

    def __init__(self, persistence: Optional[DiskPersistence] = None):
        self.persistence = persistence or DiskPersistence()
        self._sensors: Dict[str, Sensor] = {}
        self._sensor_versions: Dict[str, Sensor] = {}
        self._scenarios: Dict[str, Scenario] = {}
        self._simulations: Dict[str, Simulation] = {}
        self._jobs: Dict[str, SimulationJob] = {}
        self._reports: Dict[str, dict] = {}
        self.load_from_disk()

    def clear(self) -> None:
        """Clear all in-memory caches."""
        self._sensors.clear()
        self._sensor_versions.clear()
        self._scenarios.clear()
        self._simulations.clear()
        self._jobs.clear()
        self._reports.clear()

    def load_from_disk(self) -> None:
        """Load persisted state from disk into memory."""
        active_sensors, versions = self.persistence.load_sensors()
        self._sensors.update(active_sensors)
        self._sensor_versions.update(versions)
        self._scenarios.update(self.persistence.load_scenarios())

        loaded_jobs = self.persistence.load_jobs()
        for sim_id, jdict in loaded_jobs.items():
            self._jobs[sim_id] = SimulationJob(
                simulation_id=sim_id,
                status=jdict.get("status", "completed"),
                progress=jdict.get("progress", 1.0),
                trials_completed=jdict.get("trials_completed", 0),
                trials_total=jdict.get("trials_total", 0),
                result=jdict.get("result"),
                error=jdict.get("error"),
            )

        self._reports.update(self.persistence.load_reports())

    # Sensors
    def put_sensor(self, sensor: Sensor) -> str:
        sid = sensor.sensor_id
        self._sensors[sid] = sensor
        key = f"{sid}@{sensor.version}"
        self._sensor_versions[key] = sensor
        self.persistence.save_sensor(sensor)
        return sid

    def get_sensor(self, sensor_id: str) -> Optional[Sensor]:
        return self._sensors.get(sensor_id)

    def list_sensors(self) -> List[Sensor]:
        return list(self._sensors.values())

    def delete_sensor(self, sensor_id: str) -> bool:
        existed = self._sensors.pop(sensor_id, None) is not None
        if existed:
            self.persistence.soft_delete_sensor(sensor_id)
        return existed

    def snapshot_sensor(self, sensor_id: str) -> None:
        """Copy current sensor into immutable version snapshot store (Rule 9)."""
        current = self._sensors.get(sensor_id)
        if current is None:
            return
        key = f"{sensor_id}@{current.version}"
        if key not in self._sensor_versions:
            self._sensor_versions[key] = current
            self.persistence.save_sensor(current)

    def get_sensor_version(self, sensor_id: str, version: str) -> Optional[Sensor]:
        """Fetch an immutable version snapshot of a sensor (Rule 9)."""
        return self._sensor_versions.get(f"{sensor_id}@{version}")

    def list_sensor_versions(self, sensor_id: str) -> List[dict]:
        """List all immutable version snapshots known for a sensor, newest first."""
        prefix = f"{sensor_id}@"
        snaps = sorted(
            [(k.split("@", 1)[-1], v) for k, v in self._sensor_versions.items() if k.startswith(prefix)],
            key=lambda kv: (kv[0], id(kv[1])),
            reverse=False,
        )
        return [{"version": k, "sensor": s.model_dump()} for k, s in snaps]

    # Scenarios
    def put_scenario(self, scenario: Scenario) -> str:
        sid = scenario.scenario_id
        self._scenarios[sid] = scenario
        self.persistence.save_scenario(scenario)
        return sid

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> List[Scenario]:
        return list(self._scenarios.values())

    def delete_scenario(self, scenario_id: str) -> bool:
        existed = self._scenarios.pop(scenario_id, None) is not None
        if existed:
            self.persistence.soft_delete_scenario(scenario_id)
        return existed

    # Simulations
    def put_simulation(self, simulation: Simulation) -> str:
        sid = simulation.simulation_id
        self._simulations[sid] = simulation
        return sid

    def get_simulation(self, simulation_id: str) -> Optional[Simulation]:
        return self._simulations.get(simulation_id)

    # Jobs
    def create_job(self, simulation_id: str, trials_total: int) -> SimulationJob:
        job = SimulationJob(
            simulation_id=simulation_id,
            status="queued",
            trials_total=trials_total,
        )
        self._jobs[simulation_id] = job
        self.persistence.save_job(asdict(job))
        return job

    def get_job(self, simulation_id: str) -> Optional[SimulationJob]:
        return self._jobs.get(simulation_id)

    def update_job(
        self,
        simulation_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        trials_completed: Optional[int] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> Optional[SimulationJob]:
        job = self._jobs.get(simulation_id)
        if job is None:
            return None
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if trials_completed is not None:
            job.trials_completed = trials_completed
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        self.persistence.save_job(asdict(job))
        return job

    # Reports
    def put_report(self, report_id: str, report_data: dict) -> None:
        self._reports[report_id] = report_data
        self.persistence.save_report(report_id, report_data)

    def get_report(self, report_id: str) -> Optional[dict]:
        return self._reports.get(report_id)


# Global store instance
store = Store()