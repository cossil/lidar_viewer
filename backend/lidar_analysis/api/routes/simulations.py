"""Simulation routes (PRD sections 58-59, contract 17-19).

POST   /api/simulations
GET    /api/simulations/{id}
GET    /api/simulations/{id}/results
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from ..store import store
from ..assumptions import record_default_assumptions

router = APIRouter()


def _missing_detection_params(sensor):
    """Collect sensor parameters required by the datasheet-envelope fallback detection model
    that are unknown or missing (PRD §27 insufficient-data response)
    Returns a list of dot-paths of the offending parameters."""
    from ...models.common import ParameterStatus
    from ...models.parameter import Parameter
    missing = []
    if sensor.range is None or sensor.range.maximum is None:
        missing.append("range.maximum")
    else:
        rmax = sensor.range.maximum
        if rmax.status == ParameterStatus.UNKNOWN or rmax.value is None:
            missing.append("range.maximum")
    if sensor.beam is None or sensor.beam.horizontal_divergence is None:
        missing.append("beam.horizontal_divergence")
    else:
        bdiv = sensor.beam.horizontal_divergence
        if bdiv.status == ParameterStatus.UNKNOWN or bdiv.value is None:
            missing.append("beam.horizontal_divergence")
    return missing


class MonteCarloConfig(BaseModel):
    """Monte Carlo simulation knobs."""
    enabled: bool = True
    trials: int = 10000
    random_seed: int =123456


class MeasurementModelConfig(BaseModel):
    """Measurement error model knobs."""
    range_bias: float = 0.0
    range_sigma: float = 0.0002
    range_error_definition: str = "1sigma"


class SimulationRequest(BaseModel):
    """Request body for creating a simulation (contract section 17)."""
    scenario_id: str
    mode: str = "monte_carlo"
    duration: float =  1.0
    monte_carlo: MonteCarloConfig = MonteCarloConfig()
    detection_model_id: Optional[str] = None
    measurement_model: MeasurementModelConfig = MeasurementModelConfig()


class SimulationStatus(BaseModel):
    """Simulation job status (contract section 18)."""
    simulation_id: str
    status: str
    progress: float
    trials_completed: int
    trials_total: int


@router.post("", status_code=202)
def create_simulation(request: SimulationRequest):
    """Create and queue a simulation job (contract section 17).

    For MVP, runs synchronously but reports status "queued". In production, would use background tasks.
    """
    valid_modes = {"monte_carlo", "analytical", "synthetic_point_cloud"}
    if request.mode not in valid_modes:
        raise HTTPException(status_code=422, detail=f"mode {request.mode!r} not supported")

    scenario = store.get_scenario(request.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario {request.scenario_id} not found")

    sensor = store.get_sensor(scenario.sensor_id)
    if sensor is None:
        raise HTTPException(status_code=404, detail=f"Sensor {scenario.sensor_id} not found")

    # §27 insufficient-data guard: the datasheet-envelope fallback needs certain sensor
    # parameters; if they are unknown or missing, respond with the insufficient-data body
    missing_params = _missing_detection_params(sensor)
    if missing_params:
        return JSONResponse(
            status_code=409,
            content={
                "status": "insufficient_data",
                "missing_parameters": missing_params,
                "message": "Cannot run simulation: sensor is missing required parameters for the datasheet-envelope detection model",
            },
        )

    # Reference the immutable sensor version used for this run (Rule 9)
    sensor_version = sensor.version

    import uuid
    sim_id = f"sim_{uuid.uuid4().hex[:8]}"

    # Record the canonical assumptions for this run (PRD §61, Simulation->Assumptions)
    assumption_ids = record_default_assumptions(sim_id)

    n_trials = request.monte_carlo.trials
    seed = request.monte_carlo.random_seed

    # Create job (queued)
    job = store.create_job(sim_id, n_trials)

    # Run simulation (synchronous for MVP; surfaces status through GET endpoints)
    try:
        store.update_job(sim_id, status="running")

        import numpy as np
        from ...geometry.targets import Cylinder
        from ...physics.detection import DatasheetModel
        from ...physics.measurement import MeasurementConfig, MeasurementModel
        from ...scan.scanners import MechanicalSpinningScanner, Channel
        from ...simulation.engine import SingleTrialEngine
        from ...simulation.monte_carlo import MonteCarloEngine

        # Build target from scenario
        target_pos = scenario.target.position  # List[float]
        target_axis = scenario.target.orientation  # List[float]
        target = Cylinder.from_dbh(
            scenario.target.diameter or 0.10,
            target_pos,
            target_axis,
            scenario.target.reflectivity,
        )

        # Build scanner from sensor (sensor model doesn't carry channels)
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
        scan_points = scanner.generate_scan_points(duration=request.duration)

        # Build engine (measurement model from sensor defaults or request knobs)
        mm = MeasurementConfig(bias=request.measurement_model.range_bias, sigma=request.measurement_model.range_sigma)
        measurement_model = MeasurementModel(range_config=mm, angular_config=mm)
        engine = SingleTrialEngine(
            target=target,
            detection_model=DatasheetModel(max_range=max_range_val),
            measurement_model=measurement_model,
            beam_divergence=beam_div,
            rng=np.random.default_rng(seed),
        )

        # Run simulation by mode (all share the same engine)
        sensor_pos = np.array(scenario.sensor_pose.position)

        if request.mode == "monte_carlo":
            mo = MonteCarloEngine(engine, n_trials=n_trials, seed=seed)
            result = mo.run(scan_points, sensor_pos)
            result_dict = {
                "mode": "monte_carlo",
                "n_trials": result.n_trials,
                "seed": result.seed,
                "p_detected": result.p_detected,
                "p_reliable": result.p_reliable,
                "p_characterized": result.p_characterized,
                "detection_count_stats": {
                    "mean": result.detection_count_stats.mean,
                    "median": result.detection_count_stats.median,
                    "std": result.detection_count_stats.std,
                    "min": result.detection_count_stats.min,
                    "max": result.detection_count_stats.max,
                },
                "expected_returns_stats": {
                    "mean": result.expected_returns_stats.mean,
                    "median": result.expected_returns_stats.median,
                    "std": result.expected_returns_stats.std,
                },
            }
        elif request.mode == "analytical":
            from ...simulation.analytical import run_analytical
            ar = run_analytical(engine, scan_points, sensor_pos)
            result_dict = {
                "mode": "analytical",
                "expected_returns": ar.expected_returns,
                "expected_detections": ar.expected_detections,
                "coverage": ar.coverage,
                "range_uncertainty": ar.range_uncertainty,
            }
        else:  # synthetic_point_cloud
            from ...simulation.pointcloud import generate_point_cloud
            pc = generate_point_cloud(engine, scan_points, sensor_pos)
            result_dict = {
                "mode": "synthetic_point_cloud",
                "point_count": pc.point_count,
                "points": pc.points,
            }

        # Reference the immutable sensor version and assumptions used (Rules 9-10, PRD §61)
        result_dict["sensor_version"] = sensor_version
        result_dict.setdefault("seed", 0)
        result_dict["assumptions"] = assumption_ids

        store.update_job(
            sim_id,
            status="completed",
            progress=1.0,
            trials_completed=n_trials,
            result=result_dict,
        )

    except Exception as e:
        store.update_job(sim_id, status="failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    return {"simulation_id": sim_id, "status": "queued"}


@router.get("/{simulation_id}")
def get_simulation(simulation_id: str):
    """Get simulation job status (contract section 18)."""
    job = store.get_job(simulation_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    return {
        "simulation_id": job.simulation_id,
        "status": job.status,
        "progress": job.progress,
        "trials_completed": job.trials_completed,
        "trials_total": job.trials_total,
    }


@router.get("/{simulation_id}/results")
def get_simulation_results(simulation_id: str):
    """Get simulation results (contract section  19).

    Returns 200 with the stored result object when the job is completed;
    409 when the job exists but is not complete; 404 when unknown.
    """
    job = store.get_job(simulation_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    if job.status != "completed":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=409,
            content={"error": "simulation_not_complete", "status": job.status},
        )

    return job.result