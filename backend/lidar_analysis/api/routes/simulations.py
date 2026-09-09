"""Simulation routes (PRD sections 58-59, contract 17-19).

POST   /api/simulations
GET    /api/simulations/{id}
GET    /api/simulations/{id}/results
POST   /api/simulations/{id}/cancel
WS     /api/simulations/{id}/ws
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

import numpy as np
from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..assumptions import record_default_assumptions
from ..detection_registry import detection_registry
from ..errors import ApiError
from ..store import store

router = APIRouter()


def _missing_detection_params(sensor):
    """Collect sensor parameters required by the datasheet-envelope fallback detection model
    that are unknown or missing (PRD §27 insufficient-data response).
    Returns a list of dot-paths of the offending parameters."""
    from ...models.common import ParameterStatus
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
    random_seed: int = 123456


class MeasurementModelConfig(BaseModel):
    """Measurement error model knobs (PRD §33-34, gap G5)."""
    range_bias: float = 0.0
    range_sigma: float = 0.0002
    range_error_definition: str = "1sigma"
    angular_bias: float = 0.0
    angular_sigma: float = 0.0
    angular_error_definition: str = "1sigma"


class SimulationRequest(BaseModel):
    """Request body for creating a simulation (contract section 17)."""
    scenario_id: str
    mode: str = "monte_carlo"
    duration: float = 1.0
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


def _execute_simulation_job(
    sim_id: str,
    request: SimulationRequest,
    scenario,
    sensor,
    sensor_version: str,
    assumption_ids: list,
) -> None:
    """Worker executing the simulation in background / async task."""
    try:
        job = store.get_job(sim_id)
        if job and job.status == "cancelled":
            return

        store.update_job(sim_id, status="running", progress=0.05)

        from ...geometry.targets import Cylinder
        from ...physics.measurement import MeasurementConfig, MeasurementModel
        from ...scan.scanners import MechanicalSpinningScanner, Channel
        from ...simulation.engine import SingleTrialEngine
        from ...simulation.monte_carlo import MonteCarloEngine

        # Build target from scenario
        target_pos = scenario.target.position
        target_axis = scenario.target.orientation
        target = Cylinder.from_dbh(
            scenario.target.diameter or 0.10,
            target_pos,
            target_axis,
            scenario.target.reflectivity,
        )

        # Build scanner from sensor
        channels = [Channel(elevation_angle=0.0)]
        pr_val = sensor.scan.point_rate.value if sensor.scan and sensor.scan.point_rate else 100000
        rf_val = sensor.scan.rotation_frequency.value if sensor.scan and sensor.scan.rotation_frequency else 10
        beam_div = sensor.beam.horizontal_divergence.value if sensor.beam and sensor.beam.horizontal_divergence else 0.003

        scanner = MechanicalSpinningScanner(
            horizontal_fov=2 * np.pi,
            vertical_fov=0.5,
            channels=channels,
            point_rate=pr_val,
            rotation_frequency=rf_val,
        )
        scan_points = scanner.generate_scan_points(duration=request.duration)

        # Build measurement configs (Range + Angular, gap G5)
        range_cfg = MeasurementConfig(
            bias=request.measurement_model.range_bias,
            sigma=request.measurement_model.range_sigma,
        )
        angular_cfg = MeasurementConfig(
            bias=request.measurement_model.angular_bias,
            sigma=request.measurement_model.angular_sigma,
        )
        measurement_model = MeasurementModel(range_config=range_cfg, angular_config=angular_cfg)

        # Resolve detection model from registry (gap G7)
        detection_model = detection_registry.resolve(
            request.detection_model_id,
            sensor,
        )

        engine = SingleTrialEngine(
            target=target,
            detection_model=detection_model,
            measurement_model=measurement_model,
            beam_divergence=beam_div,
            rng=np.random.default_rng(request.monte_carlo.random_seed),
        )

        sensor_pos = np.array(scenario.sensor_pose.position)
        n_trials = request.monte_carlo.trials
        seed = request.monte_carlo.random_seed

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

        # Check again if cancelled before committing result
        current_job = store.get_job(sim_id)
        if current_job and current_job.status == "cancelled":
            return

        result_dict["sensor_version"] = sensor_version
        result_dict.setdefault("seed", seed if request.mode == "monte_carlo" else 0)
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


@router.post("", status_code=202)
def create_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """Create and queue a simulation job (contract section 17)."""
    valid_modes = {"monte_carlo", "analytical", "synthetic_point_cloud"}
    if request.mode not in valid_modes:
        raise HTTPException(status_code=422, detail=f"mode {request.mode!r} not supported")

    scenario = store.get_scenario(request.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario {request.scenario_id} not found")

    sensor = store.get_sensor(scenario.sensor_id)
    if sensor is None:
        raise HTTPException(status_code=404, detail=f"Sensor {scenario.sensor_id} not found")

    # §27 insufficient-data guard
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

    # Validate detection_model_id if provided
    if request.detection_model_id:
        # Will raise ApiError(422) if unrecognized
        detection_registry.resolve(request.detection_model_id, sensor)

    sensor_version = sensor.version
    sim_id = f"sim_{uuid.uuid4().hex[:8]}"
    assumption_ids = record_default_assumptions(sim_id)

    n_trials = request.monte_carlo.trials
    store.create_job(sim_id, n_trials)

    # Schedule background execution (PRD §59)
    background_tasks.add_task(
        _execute_simulation_job,
        sim_id,
        request,
        scenario,
        sensor,
        sensor_version,
        assumption_ids,
    )

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
    """Get simulation results (contract section 19)."""
    job = store.get_job(simulation_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    if job.status != "completed":
        return JSONResponse(
            status_code=409,
            content={"error": "simulation_not_complete", "status": job.status},
        )

    return job.result


@router.post("/{simulation_id}/cancel")
def cancel_simulation(simulation_id: str):
    """Cancel a running or queued simulation job."""
    job = store.get_job(simulation_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    if job.status in ("queued", "running"):
        store.update_job(simulation_id, status="cancelled")
        return {"simulation_id": simulation_id, "status": "cancelled"}

    return {"simulation_id": simulation_id, "status": job.status, "message": "Cannot cancel completed job"}


@router.websocket("/{simulation_id}/ws")
async def simulation_progress_ws(websocket: WebSocket, simulation_id: str):
    """WebSocket streaming progress updates for a simulation job (PRD §59)."""
    await websocket.accept()
    try:
        while True:
            job = store.get_job(simulation_id)
            if job is None:
                await websocket.send_json({"error": "unknown_simulation", "simulation_id": simulation_id})
                break

            await websocket.send_json({
                "simulation_id": job.simulation_id,
                "status": job.status,
                "progress": job.progress,
                "trials_completed": job.trials_completed,
                "trials_total": job.trials_total,
            })

            if job.status in ("completed", "failed", "cancelled"):
                break

            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass