"""In-memory data store (MVP).

For Phase 9, stores sensors, scenarios, and simulation jobs in dicts.
Will be replaced by a database in Phase  10+.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..models.sensor import Sensor
from ..models.scenario import Scenario
from ..models.simulation import Simulation


@dataclass
class SimulationJob:
    """Simulation job with status tracking (PRD section 59)."""

    simulation_id: str
    status: str  # queued | running | completed | failed | cancelled
    progress: float = 0.0
    trials_completed: int = 0
    trials_total: int =  0 
    result: Optional[dict] = None
    error: Optional[str] = None


class Store:
    """Thread-safe in-memory store."""

    def __init__(self):
        self._sensors: Dict[str, Sensor] = {}
        self._sensor_versions: Dict[str, Sensor] = {}
        self._scenarios: Dict[str, Scenario] = {}
        self._simulations: Dict[str, Simulation] = {}
        self._jobs: Dict[str, SimulationJob] = {}

    # Sensors
    def put_sensor(self, sensor: Sensor) -> str:
        sid = sensor.sensor_id
        self._sensors[sid] = sensor
        return sid

    def get_sensor(self, sensor_id: str) -> Optional[Sensor]:
        return self._sensors.get(sensor_id)



    def list_sensors(self) -> List[Sensor]:
        return list(self._sensors.values())



    def delete_sensor(self, sensor_id: str) -> bool:
        return self._sensors.pop(sensor_id, None) is not None

    def snapshot_sensor(self, sensor_id: str) -> None:
        """Copy the current (latest) sensor into the immutable version snapshot store,
        keyed by `f"{sensor_id}@{version}"`, if not already present.



        Simulation runs reference this pinned snapshot so an immutable version (Rule 9)
        is retained even if the sensor is later PUT-updated."""
        current = self._sensors.get(sensor_id)
        if current is None:
            return
        key = f"{sensor_id}@{current.version}"
        self._sensor_versions.setdefault(key, current)

    def get_sensor_version(self, sensor_id: str, version: str) -> Optional[Sensor]:
        """Fetch an immutable version snapshot of a sensor (Rule 9)."""
        return self._sensor_versions.get(f"{sensor_id}@{version}")



    def list_sensor_versions(self, sensor_id: str) -> List[dict]:
        """List all immutable version snapshots known for a sensor, newest first."""
        prefix = f"{sensor_id}@"
        snaps = sorted(
            [(k.split("@", 1)[-1], v) for k, v in self._sensor_versions.items() if k.startswith(prefix)],
            key=lambda kv: (kv[0], id(kv[1])), reverse=False,
        )
        return [{"version": k, "sensor": s.model_dump()} for k, s in snaps]



    # Scenarios
    def put_scenario(self, scenario: Scenario) -> str:
        sid = scenario.scenario_id
        self._scenarios[sid] = scenario
        return sid

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        return self._scenarios.get(scenario_id)



    def list_scenarios(self) -> List[Scenario]:
        return list(self._scenarios.values())



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
        return job


# Global store instance
store = Store()