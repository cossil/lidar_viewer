# Implementation Conventions (all builder/critic agents MUST read)

This is the shared ground rules for the LiDAR Performance Analysis & Simulation Platform.

## Source of truth
The two authoritative documents are in `/opt/data/lidar_platform/docs/`:
- `LiDAR_Performance_Analysis_and_Simulation_Platform_-_Product_Requirements_Document.md` (PRD)
- `LiDAR_Performance_Analysis_Platform_-_Formal_Data_Schemas_and_API_Contracts.md` (SCHEMAS/API contract)

Quote requirements directly from these when implementing or when criticizing. Do NOT invent requirements.

## Project root
`/opt/data/lidar_platform`. Python package root = `backend/lidar_analysis` (imports are `lidar_analysis.models...`).

## Environment
- python: `/opt/data/lidar_platform/.venv/bin/python`
- Run tests: from project root:  `.venv/bin/python -m pytest backend/tests/<file> -q`
- PYTHONPATH: tests rely on a `conftest.py`/ `pytest.ini` rootdir; when running modules directly prepend `PYTHONPATH=backend`.
- Add the spec docs to a fixture string; do NOT re-download from network.

## Rules for code
1. SI units internally: meters, radians, seconds,reflectivity normalized 0–1, probability 0–1. Conversions only at API/UI boundary.
2. Unknown parameters are `value=None`, `status="unknown"` — never zero, never inferred. (PRD §5.4; SCHEMAS Rule 7,8.
3. Never fabricate detection probability. If the selected detection model needs a parameter whose status is `unknown`, return `insufficient_data` — not a fabricated probability. (PRD §32; SCHEMAS §27, business Rule  ‎8.
4. Determinism/reproducibility: every stochastic function takes an explicit `rng` or `seed`; never use global `np.random` without seed. Simulation must record seed.(SCHEMAS §36; PRD §53,69.
5. Separate model layers — geometry, scanning, optics, detection, measurement, monte_carlo, analysis must be distinct modules; never one monolithic function. (PRD §79 Rule 5.
6. Provenance is mandatory on every externally sourced sensor parameter. `DataType`/`Origin` enums strictly from SCHEMAS §2.1.
7. Parameter classification: values are wrapped as `{value, unit, origin, status, definition, conditions, provenance}` per parameter.json. Do not store raw numbersas top-level sensor params.

## Enums (exact strings; SCHEMAS §2.1)
- Origin: `SOURCE, USER_DEFINED, DERIVED, ASSUMED, MODELED, SIMULATED, EMPIRICAL`
- Parameter status: `known, unknown, not_applicable, estimated`
- Error definition: `1sigma, 2sigma, 95_percent, rms, maximum, unspecified`
- sensor_type / scan.type: `mechanical_spinning, structured_raster, non_repetitive, other`
- detection model_type: `datasheet, analytical, empirical, assumption`
- Simulation mode: `analytical, monte_carlo, synthetic_point_cloud`
- Job status: `queued, running, completed, failed, cancelled`
- Validation status: `unvalidated, partially_validated, validated`
- Suitability classification: `suitable, conditionally_suitable, not_suitable, insufficient_data`
- Physical-model confidence: `high, moderate, low, insufficient`

## Pydantic strictness
Use Pydantic v2 with:
- `model_config = ConfigDict(extra="forbid", validate_assignment=True)`
- `field_validator` for bounds: probability 0–1, reflectivity 0.1–1.0, DBH 0.05–1.0 m, duration 0, MC trials 1–100000, pitch ±π/2, cylinder diameter range. (SCHEMAS business Rules ‎1–‎6;
- unknown numeric params: `value: float | None` + `status: str = "known"`.

## API
Base path `/api/v1`. Error contract exactly per SCHEMAS §25 (object `{error:{code,message,field,details}}` with the listed codes). Endpoints per SCHEMAS §13–§24. Versioning per §28. Pydantic models une FastAPI → OpenAPI. Backend must enforce validation independently of frontend. (§40,

## Geometry
- Right-handed Cartesian world frame; LiDAR pose as 4×4 homogeneous `T_L` `[[R,p],[0,1]]]`. (PRD §14),
- Target: cylinder (ideal trunk) params DBH→radius r=D/2 and box. 3D transforms compose via matrices/quaternions, not manual Euler chaining.
- Cylinder ray intersection: analytical solve ray-cylinder; returns hit, point, true range, normal, surface id..
- angular size cylinder: θ_T = 2 atan(D/(2R)). incidence: α=acos(|n·(-d)|), clamped 0–π/2..(PRD §19,§27,
- beam footprint: `d_b = 2R tan(θ_b/2)`; never assume divergence==angiular resolution unless explicitly configured. (PRD §25,

## Numerical
Use numpy vectorization wherever feasible; pytest tests compare against known analytical solutions within tight tol. Level1 mathematical validation required (PRD §63; Level2 synthetic validation §64. 

## Testing
- tests live under `backend/tests/<unit>/`; use pytest.
- Contract tests verify: valid accepted, invalid rejected, missing field rejected, bad unit rejected, bad range rejected, bad prob rejected, unknown sensor rejected, incompatible model rejected, insufficient-data correctly reported. (SCHEMAS §39,
- Level2 synthetic: ideal target → returns per model; ray outside → none; P_d=0 → zero detections; P_d=1 → all intersecting rays detected. (PRD §64,

## Report & exports
- CSV for numerical data; JSON for sensors/scenarios/simulations/results; Markdown engineering report with sections per PRD §83.