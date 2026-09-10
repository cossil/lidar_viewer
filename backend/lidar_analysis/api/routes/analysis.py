"""Analysis routes (PRD section 58, API schemas sections 20-25).

POST   /api/analysis/distance-sweep
POST   /api/analysis/dbh-sweep
POST   /api/analysis/compare
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from typing import Any, Dict, List, Optional

import numpy as np

from ...geometry.targets import Cylinder
from ...physics.detection import DatasheetModel
from ...physics.measurement import MeasurementConfig, MeasurementModel
from ...scan.scanners import MechanicalSpinningScanner, Channel
from ...simulation.engine import SingleTrialEngine
from ...simulation.monte_carlo import MonteCarloEngine
from ...simulation.analysis import distance_sweep, find_effective_ranges
from ..store import store
from ..errors import ApiError

router = APIRouter()


class DistanceSweepRange(BaseModel):
    start: float = 10.0
    end: float = 80.0
    step: float = 10.0


class SimulationConfig(BaseModel):
    duration: float = 1.0
    monte_carlo_trials: int = 1000
    random_seed: int = 123456


class DistanceSweepRequest(BaseModel):
    scenario_id: str
    distance: DistanceSweepRange = DistanceSweepRange()
    simulation: SimulationConfig = SimulationConfig()


class CompareScenario(BaseModel):
    target_type: str = "cylinder"
    dbh: float = 0.10
    distance: float = 30.0
    reflectivity: float = 0.3
    incidence_angle: float = 0.0


class CompareRequest(BaseModel):
    sensor_ids: List[str]
    scenario: CompareScenario = CompareScenario()
    simulation: SimulationConfig = SimulationConfig()


class DbhSweepRequest(BaseModel):
    scenario_id: str
    dbh: Dict[str, float]
    distance: float = 30.0
    simulation: Dict[str, Any] = {}


def _build_engine(sensor, target_dbh, distance, reflectivity, seed=42):
    """Build a SingleTrialEngine from a sensor config."""
    target = Cylinder.from_dbh(target_dbh, [distance, 0, 0], [0, 0, 1], reflectivity)
    channels = [Channel(elevation_angle=0.0)]
    max_range_val = sensor.range.maximum.value if sensor.range and sensor.range.maximum else 200
    pr_val = sensor.scan.point_rate.value if sensor.scan.point_rate else 100000
    rf_val = sensor.scan.rotation_frequency.value if sensor.scan.rotation_frequency else 10
    beam_div = sensor.beam.horizontal_divergence.value if sensor.beam and sensor.beam.horizontal_divergence else 0.003
    acc_val = sensor.accuracy.range.value if sensor.accuracy and sensor.accuracy.range else 0.02
    scanner = MechanicalSpinningScanner(
        horizontal_fov=2 * np.pi,
        vertical_fov=0.5,
        channels=channels,
        point_rate=pr_val,
        rotation_frequency=rf_val,
    )
    sigma_min = None
    sigma_max = None
    d_max = float(max_range_val)
    if sensor.precision and getattr(sensor.precision, "range_min", None) and sensor.precision.range_min.value is not None:
        sigma_min = float(sensor.precision.range_min.value)
    if sensor.precision and getattr(sensor.precision, "range_max_10pct", None) and sensor.precision.range_max_10pct.value is not None:
        sigma_max = float(sensor.precision.range_max_10pct.value)

    returns_per_pulse = 1
    if sensor.scan and getattr(sensor.scan, "returns_per_pulse", None) is not None:
        returns_per_pulse = int(sensor.scan.returns_per_pulse)

    mm = MeasurementConfig(
        bias=0.0,
        sigma=acc_val * 0.01,
        sigma_min=sigma_min,
        sigma_max=sigma_max,
        d_max=d_max,
    )
    measurement_model = MeasurementModel(range_config=mm, angular_config=mm)
    engine = SingleTrialEngine(
        target=target,
        detection_model=DatasheetModel(max_range=max_range_val),
        measurement_model=measurement_model,
        beam_divergence=beam_div,
        rng=np.random.default_rng(seed),
        returns_per_pulse=returns_per_pulse,
    )
    return engine, scanner


@router.post("/distance-sweep")
def run_distance_sweep(request: DistanceSweepRequest):
    scenario = store.get_scenario(request.scenario_id)
    if scenario is None:
        raise ApiError(
            status_code=404,
            code="UNKNOWN_SCENARIO",
            message=f"Scenario {request.scenario_id} not found",
            field="scenario_id",
        )

    sensor = store.get_sensor(scenario.sensor_id)
    if sensor is None:
        raise ApiError(
            status_code=404,
            code="UNKNOWN_SENSOR",
            message=f"Scenario {request.scenario_id} references sensor {scenario.sensor_id} which was not found",
            field="scenario_id",
        )

    reflectivity = scenario.target.reflectivity
    dist_cfg = request.distance
    if dist_cfg.step <= 0:
        raise ApiError(
            status_code=422,
            code="INVALID_PARAMETER",
            message="distance.step must be > 0",
            field="distance.step",
        )

    distances = [max(0.0, float(v)) for v in np.arange(dist_cfg.start, dist_cfg.end + dist_cfg.step, dist_cfg.step)]

    sim_cfg = request.simulation
    n_trials = int(sim_cfg.monte_carlo_trials)
    seed = int(sim_cfg.random_seed)

    def factory(dist):
        engine, _ = _build_engine(sensor, scenario.target.diameter, dist, reflectivity, seed)
        return engine

    _, scanner = _build_engine(sensor, scenario.target.diameter, distances[0], reflectivity, seed)
    scan_points = scanner.generate_scan_points(duration=sim_cfg.duration)

    sweep = distance_sweep(
        engine_factory=factory,
        distances=np.array(distances),
        n_trials=n_trials,
        seed=seed,
        scan_points=scan_points,
        sensor_position=np.array([0, 0, 0.0]),
    )
    ranges = find_effective_ranges(sweep)

    points = [
        {
            "distance": p.distance,
            "p_detected": p.p_detected,
            "p_reliable": p.p_reliable,
            "p_characterized": p.p_characterized,
            "expected_returns": p.expected_returns,
        }
        for p in sweep.points
    ]

    return {
        "analysis_id": f"sweep_{uuid.uuid4().hex[:8]}",
        "status": "queued",
        "points": points,
        "effective_ranges": {
            "detection_range": ranges.detection_range,
            "reliable_range": ranges.reliable_range,
            "characterization_range": ranges.characterization_range,
        },
    }


def _run_scenario_sweep(sensor, scenario, dbh_values, distance, n_trials, seed):
    """Run a small Monte Carlo sweep for each DBH value."""
    def factory(dbh_val):
        engine, _ = _build_engine(sensor, dbh_val, distance, scenario.target.reflectivity, seed)
        return engine

    points_array = np.array(dbh_values)
    sweep = distance_sweep(
        engine_factory=factory,
        distances=points_array,
        n_trials=n_trials,
        seed=seed,
        scan_points=[],
        sensor_position=np.array([0, 0, 0.0]),
    )
    return [
        {
            "dbh": p.distance,
            "p_detected": p.p_detected,
            "p_reliable": p.p_reliable,
            "p_characterized": p.p_characterized,
        }
        for p in sweep.points
    ]


@router.post("/dbh-sweep")
def run_dbh_sweep(request: DbhSweepRequest):
    scenario = store.get_scenario(request.scenario_id)
    if scenario is None:
        raise ApiError(
            status_code=404,
            code="UNKNOWN_SCENARIO",
            message=f"Scenario {request.scenario_id} not found",
            field="scenario_id",
        )

    sensor = store.get_sensor(scenario.sensor_id)
    if sensor is None:
        raise ApiError(
            status_code=404,
            code="UNKNOWN_SENSOR",
            message=f"Scenario {request.scenario_id} references sensor {scenario.sensor_id} which was not found",
            field="scenario_id",
        )

    dbh_cfg = request.dbh
    start = float(dbh_cfg.get("start", 0.10))
    end = float(dbh_cfg.get("end", 0.10))
    step = float(dbh_cfg.get("step", 0.1))
    if step <= 0:
        raise ApiError(
            status_code=422,
            code="INVALID_PARAMETER",
            message="dbh.step must be > 0",
            field="dbh.step",
        )

    dbh_values = [max(0.0, float(v)) for v in np.arange(start, end + step, step)]

    sim_cfg = request.simulation or {}
    n_trials = int(sim_cfg.get("monte_carlo_trials", 50))
    seed = int(sim_cfg.get("random_seed", 42))

    points = _run_scenario_sweep(
        sensor=sensor,
        scenario=scenario,
        dbh_values=dbh_values,
        distance=request.distance,
        n_trials=n_trials,
        seed=seed,
    )

    return {
        "analysis_id": f"dbhsweep_{uuid.uuid4().hex[:8]}",
        "status": "completed",
        "points": points,
    }


@router.post("/compare")
def run_comparison(request: CompareRequest):
    """Compare multiple sensors under identical conditions (schema section 22-23)."""
    scenario = request.scenario

    results = []
    for sid in request.sensor_ids:
        sensor = store.get_sensor(sid)
        if sensor is None:
            raise ApiError(
                status_code=404,
                code="UNKNOWN_SENSOR",
                message=f"Sensor {sid} not found",
                field="sensor_ids",
            )

        sim_cfg = request.simulation

        _, scanner = _build_engine(
            sensor,
            scenario.dbh,
            scenario.distance,
            scenario.reflectivity,
            sim_cfg.random_seed,
        )
        scan_points = scanner.generate_scan_points(duration=sim_cfg.duration)

        # Build a scratch engine at the exact requested distance so every sensor
        # sees an identical fixed-dbh cylinder target.
        engine, _ = _build_engine(
            sensor,
            scenario.dbh,
            scenario.distance,
            scenario.reflectivity,
            sim_cfg.random_seed,
        )
        mc = MonteCarloEngine(engine, n_trials=sim_cfg.monte_carlo_trials, seed=sim_cfg.random_seed)
        result = mc.run(scan_points=scan_points, sensor_position=np.array([0, 0, 0.0]))

        results.append(
            {
                "sensor_id": sid,
                "detection_probability": result.p_detected,
                "expected_returns": result.expected_returns_stats.mean,
                "reliable_probability": result.p_reliable,
                "characterization_probability": result.p_characterized,
            }
        )

    return {
        "comparison_id": f"cmp_{uuid.uuid4().hex[:8]}",
        "conditions": {
            "dbh": scenario.dbh,
            "distance": scenario.distance,
            "reflectivity": scenario.reflectivity,
            "incidence_angle": scenario.incidence_angle,
            "duration": request.simulation.duration,
        },
        "sensors": results,
    }