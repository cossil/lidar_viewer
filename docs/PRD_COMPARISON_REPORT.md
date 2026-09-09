# PRD vs. Implementation — Completeness & Gap Report

**Project:** LiDAR Performance Analysis & Simulation Platform (SilvaLab / Univ. of Florida)
**Backend:** `/opt/data/lidar_platform`
**Report date:** 2026-09-08
**Basis:** PRD (`docs/LiDAR_Performance_Analysis_and_Simulation_Platform_-_Product_Requirements_Document.md`, 2920 lines), SCHEMAS/API contract (`docs/…_Formal_Data_Schemas_and_API_Contracts.md`, 2930 lines), live code inspection, and the full test suite (245 tests passing).

---

## 0. How to read this report

Each section below maps a PRD grouping to the actual code. Status is per item:

- **✅ Implemented & tested** — code present, covered by tests.
- **🟡 Partial** — core present but one or more sub-items missing/drifted from the spec.
- **❌ Missing** — not implemented.

File paths are relative to the project root. The implementation is organized as a layered engine (models → geometry → scan → physics → simulation → analysis → reporting → API), mirroring the "Sensor Model → … → Statistical Analysis" pipeline required by PRD §1.

---

## 1. Domain Models (PRD §8-10, §13, §15; SCHEMAS §2-8)

| PRD Item | Status | Where / Notes |
|---|---|---|
| Sensor schema | ✅ | `models/sensor.py` — full Pydantic `Sensor` with `Range`, `Accuracy`, `Precision`, `Angular`, `Beam`, `Scan`, `Optical`, `DetectionModelReference`, `Validation`. `extra="forbid"`, `validate_assignment=True`. |
| Provenance | ✅ | `models/provenance.py`; DataOrigin enum in `models/common.py` (exact SCHEMAS §2.1 strings). |
| Assumptions | ✅ | `models/sensor.py::Assumption`, `api/assumptions.py` registry (PRD §61). |
| Scenario schema | ✅ | `models/scenario.py` — environment, sensor_pose, target (cylinder + explicit position/orientation). |
| Target schema (Box + Cylinder/Tree trunk) | ✅ | `models/scenario.py` target types; `geometry/targets.py` has `Cylinder` and `Box`. |
| Parameter value schema | ✅ | `models/parameter.py` — `{value, unit, origin, status, definition, conditions, provenance}`, enforces value=None ⇔ unknown. |
| DetectionModel schema | ✅ (core) | `models/detection_model.py` — `model_id`, `model_type`, `parameters`, `required_inputs`, `validity`, `provenance`, `confidence`, `output`. |
| Enumerations | ✅ | `models/common.py` — all enums match SCHEMAS §2.1 verbatim. |

**Evidence (tests):** `test_models.py` (29) — PRD §9 example sensor, §13 scenario, §32/33/34 canonical objects, unknown-parameter roundtrip, MC defaults, schema conformance, reflectivity/DBH bounds, extra-field rejection, pitch clamp, enum serialization.

---

## 2. Geometry Engine (PRD §14-19, Phase 2; SCHEMAS §?)

| PRD Item | Status | Where / Notes |
|---|---|---|
| Coordinate frames | ✅ | `geometry/transforms.py`, ENG-DEC D001 (right-handed, +X forward, +Z up). |
| Transformations (4×4) | ✅ | `geometry/transforms.py` — euler↔matrix, pose compose, invert. |
| Rays | ✅ | `geometry/rays.py` — `make_ray`, `ray_at`, `direction_from_angles`, mechanical-spin generation. |
| Box intersection | ✅ | `geometry/intersection.py` — analytical ray-box (incl. rotated box). |
| Cylinder intersection | ✅ | `geometry/intersection.py` — analytical ray-cylinder (hit/miss/oblique/from-behind). |
| Surface normals | ✅ | `geometry/targets.py` — cylinder/box surface normals. |
| Angular size θ_T | ✅ | `geometry/angular_size.py` — `2·atan(D/(2R))` (PRD §19 example verified). |
| Beam footprint | ✅ | `geometry/angular_size.py::beam_footprint`. |
| Incidence angle | ✅ | `geometry/angular_size.py` — clamped 0–π/2. |

**Evidence:** `test_geometry.py` (43).

---

## 3. Scan Engine (PRD Phase 3; §24)

| PRD Item | Status | Where / Notes |
|---|---|---|
| Base scanner interface | ✅ | `scan/scanners.py` (mechanisms, generator interface). |
| Mechanical spinning scanner | ✅ | `MechanicalSpinningScanner` — multi-channel, point-rate cap (D018). |
| Structured raster scanner | ✅ | `StructuredRasterScanner` — raster ordering. |
| Non-repetitive scanner | ✅ | `NonRepetitiveScanner` — FOV-bounded, deterministic with seed. |
| Scan duration independent of MC trials (PRD §24) | ✅ | Verified by dedicated test. |

**Evidence:** `test_scan.py` (15).

---

## 4. Beam / Optical, Detection, Measurement (PRD Phase 4-6, §25-32; SCHEMAS §9)

| PRD Item | Status | Where / Notes |
|---|---|---|
| Beam overlap G | ✅ | `physics/` — full/partial/none; analytical chord approximation (D007). |
| Beam footprint / effective area A_eff | ✅ | `physics/` beam+target; D019. |
| Return strength | ✅ | `physics/` — simplified deterministic model (PRD §26 allows MVP analytical approx.). |
| Reflectivity | ✅ | models + physics. |
| Detection — datasheet model | ✅ | `physics/detection.py::DatasheetModel`. |
| Detection — analytical model | ✅ | `AnalyticalModel` (physics-inspired sigmoid). |
| Detection — empirical model | ✅ | `physics/detection.py::EmpiricalModel` + `ManufacturerCurveModel`, `DetectionModelResolver` (priority 1→5, Rule 8). |
| Detection — assumption model | ✅ | `AssumptionModel`. |
| **Model confidence / insufficient data** | ✅ | `insufficient_data → None` probability, never fabricated (PRD §32, SCHEMAS §27, Rule 8). |
| Measurement — range bias | ✅ | `physics/measurement.py`. |
| Measurement — range random error | ✅ | Gaussian, seeded/deterministic. |
| Measurement — angular bias | 🟡 Partial | Measurement machinery supports angular config, but API path does not set angular bias per sensor; default used. |
| Measurement — angular random error | 🟡 Partial | Angular perturbation supported in module but not surfaced in the simulation-request path (D022 documented). |
| Error-definition conversion (1σ↔2σ↔95%) | ✅ | `measurement.py` (PRD §34). |

**Evidence:** `test_physics.py` (27), `test_detection_engine.py` (31) — Rule 8, resolver priority, empirical interpolation, insufficient-data.

---

## 5. Simulation Engine + Monte Carlo (PRD Phase 7-8, §33-38, §54; SCHEMAS §8)

| PRD Item | Status | Where / Notes |
|---|---|---|
| Candidate ray generation | ✅ | `scan/scanners.py` + `simulation/engine.py`. |
| Intersection | ✅ | `simulation/engine.py` reuses geometry. |
| Detection | ✅ | Engine orchestrates detection models. |
| Stochastic return generation | ✅ | Bernoulli via seeded RNG. |
| Measurement errors | ✅ | Applied per detected return. |
| Synthetic point cloud | ✅ | `simulation/pointcloud.py` — `(az, el, range)` rows; deterministic. |
| Monte Carlo engine (N trials) | ✅ | `simulation/monte_carlo.py` — trials 1–100,000, configurable seed, statistics. |
| Random seed recorded | ✅ | `result.seed` (all modes; analytical/pointcloud report 0). |
| Uncertainty propagation / statistical analysis | ✅ | Means, std, counts. |
| **Analytical mode** | ✅ | `simulation/analytical.py` — deterministic, matches MC mean. |
| **Point-cloud mode** | ✅ | `simulation/pointcloud.py`. |

**Evidence:** `test_simulation.py` (11), `test_modes.py` (8), `test_e2e.py` (7, Level-2 synthetic validation: P_d=0→0, P_d=1→all detected, no intersection→0).

---

## 6. Analysis (PRD §36-46, Phase 9; SCHEMAS)

| PRD Item | Status | Where / Notes |
|---|---|---|
| DETECTED / RELIABLE / CHARACTERIZED classification (§39) | ✅ | `simulation/monte_carlo.py` + `analysis.py::classify`. Defaults: discussed below (§39 gap note). |
| Detection count thresholds (N≥1 / N≥5 / N≥10) | ✅ | Enforced in MC (min_returns). |
| Geometric coverage C_g (§40) | ✅ | `simulation/analysis.py::geometric_coverage` (angular bbox, concentrated≠distributed). |
| σ_R range-noise metric (§41) | ✅ | Per-trial std of measured ranges in MC. |
| CHARACTERIZED = count≥10 ∧ C_g≥30% ∧ σ_R≤thr | ✅ | Folded into `p_characterized` (MIN section 39 gap: threshold defaulting). |
| Distance sweep + effective ranges | ✅ | `analysis.py::distance_sweep`, `find_effective_ranges` (R_char ≤ R_rel ≤ R_det ordering). |
| DBH sweep | ✅ | `analysis.py` + API `/analysis/dbh-sweep`. |
| Sensor comparison | ✅ | `analysis/comparison.py` + `/analysis/compare`. |
| Suitability assessment (PRD §46, SCHEMAS §10-11) | ✅ | `analysis/suitability.py` — suitable / conditionally_suitable / not_suitable / insufficient_data, per-criterion traceability. |

**Evidence:** `test_analysis.py` (8), `test_coverage.py` (6), `test_dbh_report.py` (5).

### §39 gap note (🟡)
The `classify()`/MC **defaults** are `min_returns_characterized=10`, `min_coverage_characterized=0.3`, `sigma_R_threshold=0.1`. The PRD wording suggests σ_R ≤ 0.05 m for "characterization" (D020 documented both 0.05 and EDITABLE defaults). The 0.1 default is editable, so this is a **default-value drift**, not a functional gap — flagging for alignment with the PRD example.

---

## 7. Backend API (PRD §58-59, Phase 10; SCHEMAS §12-25)

| Endpoint / Requirement | Status | Where / Notes |
|---|---|---|
| GET/POST /api/sensors | ✅ | `api/routes/sensors.py`. |
| GET/PUT/DELETE /api/sensors/{id} | ✅ | PUT creates immutable version + snapshots (Rule 9, D012). |
| **GET /api/sensors/{id}/versions** | ✅ | Versioning (added in latest increment). |
| POST /api/datasheets/extract | ✅ | `api/routes/datasheets.py` → `ingestion/`. |
| POST /api/datasheets/validate | ✅ | As `/datasheets/{extraction_id}/validate`. |
| GET/POST /api/scenarios | ✅ | `api/routes/scenarios.py`. |
| PUT /api/scenarios/{id} | ✅ | Added per §16. |
| POST /api/simulations | ✅ | `api/routes/simulations.py` — 202 + queued, all 3 modes, §27 guard. |
| GET /api/simulations/{id} | ✅ | Job status. |
| GET /api/simulations/{id}/results | ✅ | 200 / 409 / 404 per contract. |
| POST /api/analysis/distance-sweep | ✅ | Request `{scenario_id, distance{start,end,step}, simulation{...}}`. |
| POST /api/analysis/dbh-sweep | ✅ | |
| POST /api/analysis/compare | ✅ | Returns `comparison_id`, `conditions`, `sensors[]`. |
| POST /api/reports, GET /api/reports/{id} | ✅ | `api/routes/reports.py`. |
| Standard error envelope (§25) | 🟡 Partial | `ApiError` + handler produce `{error:{code,message,field,details}}`, but **only `ApiError`-raised paths** use it; `HTTPException` (sensors, scenarios, reports, datasheets, simulations-not-found) still returns FastAPI's default shape. |
| Async job status / WebSocket for long MC | 🟡 Partial | Jobs exist with progress counters, but execution is **synchronous** (no background task / WebSocket yet); status fields are populated but progress never updates mid-run. |
| Simulation job model (queued/running/completed/failed/cancelled) | ✅ | `store.SimulationJob`. |

**Evidence:** `test_api.py` (22), `test_modes.py` (API), `test_datasheet_api.py` (6), `test_sensor_versioning.py` (9).

---

## 8. Reporting / Export (PRD §60, Phase 13; SCHEMAS §24)

| PRD Item | Status | Where / Notes |
|---|---|---|
| CSV export (numerical) | ✅ | `reporting/csv_exporter.py` (incl. sweep & comparison CSV). |
| JSON export (sensors/scenarios/simulations/results) | ✅ | `reporting/json_exporter.py`. |
| Markdown engineering report (14 sections, PRD §83 / §60) | ✅ | `reporting/` — all 14 required sections present. |

**Evidence:** `test_reporting.py` (9), `test_dbh_report.py` (Report API).

---

## 9. Persistence (PRD §55-57, Phase 10+; SCHEMAS §33-36, D008)

| PRD Item | Status | Where / Notes |
|---|---|---|
| Primary storage = **JSON files** in `data/{sensors,scenarios,simulations,reports}` | ❌ Missing | `data/` has only placeholder `README.md` files. **Store is in-memory only** (`api/store.py`); everything is lost on restart. No file I/O, no `<id>.v<version>.json` writer, no `*.latest` pointer (D008 spec). |
| No relational DB for MVP | ✅ | None used (consistent). |
| Sensor immutable versioning on disk | 🟡 Partial | Done **in memory** (Rule 9, versions endpoint) but **not persisted to disk**. |

---

## 10. Frontend / UI / Visualization (PRD Phase 11-12, §47; SCHEMAS §31)

| PRD Item | Status | Notes |
|---|---|---|
| Dashboard | ❌ | No `frontend/` directory at all. |
| Sensor library | ❌ | |
| Sensor validation screen | ❌ | |
| Scenario builder | ❌ | |
| Simulation controls | ❌ | |
| Results dashboard | ❌ | |
| 2D plots / heatmaps / 3D geometry / point-cloud viz | ❌ | |
| Swagger UI (interactive API) | ✅ | FastAPI auto-serves `/docs` (dev convenience; not the PRD frontend). |

The PRD's browser frontend (React/TS/Vite, visualizations) **has not been started** — it is Phases 11-12, marked "pending" in PROGRESS.md. Access today is API-only via Swagger/curl.

---

## 11. Rules & Global Requirements (PRD and SCHEMAS §26, §35-36)

| Rule / Requirement | Status | Notes |
|---|---|---|
| Rule 1 — Do not invent sensor specs | ✅ | Ingestion warnings; never fabricates (test: `test_never_fabricates_unknown_value`). |
| Rule 2 — Preserve provenance | ✅ | mandatory provenance on parameters. |
| Rule 3 — Never silently change validated data | ✅ | Immutable sensor versions on PUT. |
| Rule 4 — Explicitly represent unknowns | ✅ | value=None + status=unknown throughout. |
| Rule 5 — Separate model layers | ✅ | Distinct module layers. |
| Rule 6 — Reproducibility (seed recorded) | ✅ | All modes record seed; RNG seeded. |
| Rule 7 — No hidden assumptions | ✅ | Assumption registry (§61) in simulation results. |
| Rule 8 — No fake detection probability | ✅ | insufficient_data → None. |
| Rule 9 — Test before optimization / immutable sensor versioning | ✅ | In-memory versioning + tests. (Disk persistence still missing.) |
| Rule 10 — Use SI units internally | ✅ | CONVENTIONS; conversion at API/UI boundary. |
| Level 1 — Mathematical validation (§63) | ✅ | geometry/metrics vs analytical solutions. |
| Level 2 — Synthetic validation (§64, §81 canonical fixture) | ✅ | `test_e2e.py` Level-2 cases + canonical fixture. |

---

## 12. Summary of Gaps (what's still missing / partial)

| # | Area | Gap | Severity |
|---|---|---|---|
| G1 | **Persistence** | No JSON file storage in `data/`; in-memory only (rules/SCHEMAS §33-36, D008). Data lost on restart. | **High** |
| G2 | **Frontend** | No UI/visualization at all (PRD Phases 11-12, §47). API-only. | **High** |
| G3 | **Error envelope (§25)** | `HTTPException`-based routes return non-standard error bodies; only `ApiError` routes align with the §25 contract. | Medium |
| G4 | **Async jobs** | Simulations run synchronously; progress never updates mid-run; no background task / WebSocket (§59). | Medium |
| G5 | **Angular measurement** | Angular bias/error not surfaced in the API simulation path (partial per Phase 6). | Low–Medium |
| G6 | **§39 defaults** | CHARACTERIZED σ_R default is 0.1 vs PRD example 0.05 (editable; drift only). | Low |
| G7 | **DetectionModel registry by id** | `detection_model_id` accepted but no registry of named detection models to select from (SCHEMAS §7). | Low–Medium |
| G8 | **README** | Phase 13 README not written. | Low |

---

## 13. Phase-by-Phase Completion (PRD §80 Phases 1-14)

| Phase | Status |
|---|---|
| 1 — Domain Models | ✅ 29 tests |
| 2 — Geometry Engine | ✅ 43 tests |
| 3 — Scan Engine | ✅ 15 tests |
| 4 — Beam/Optical | ✅ (physics) |
| 5 — Detection Engine | ✅ 31 detection tests |
| 6 — Measurement Model | 🟡 (angular gap G5) |
| 7 — Simulation Engine | ✅ |
| 8 — Monte Carlo | ✅ |
| 9 — Analysis | ✅ |
| 10 — Backend API | ✅ (error-envelope + async gaps G3/G4) |
| 11 — Frontend | ❌ (G2) |
| 12 — Visualization | ❌ (G2) |
| 13 — Reporting | ✅ |
| 14 — Integration Testing | ✅ 7 e2e tests |

**Full suite:** 245 tests, all green.

---

## 14. Implementation Plan for Missing / Partial Items

Priority-ordered. Each item is self-contained and testable.

### P1 — JSON file persistence (G1, High) — hardest-first
**Goal:** satisfy SCHEMAS §33-36 + D008: sensors/scenarios/simulations/reports persisted as JSON under `data/`, with immutable per-sensor versions.
1. `api/store.py`: add a `PersistenceBackend` that writes sensors to `data/sensors/<id>.v<version>.json` + `<id>.latest` pointer; mirror for scenarios, simulations (job+result), reports. Keep the in-memory dict as an L1 cache.
2. Load all JSON files into the store at startup (`Store.load()` called from `create_app`).
3. On `put_sensor`/`put_scenario`/`update_job`/report-create, write-through.
4. Tests: restart-simulation fixture (write→new Store→read same data), version file naming, latest-pointer update, `insufficient-data` and report persistence.

### P2 — Frontend + visualization (G2, High)
1. Scaffold `frontend/` (Vite + React + TS per PRD §56).
2. Screens (PRD §47): Dashboard, Sensor Library, Sensor Validation, Scenario Builder, Simulation Controls, Results dashboard.
3. Visualization (PRD Phase 12): 2D plots + distance-sweep curves (Plotly), DBH×range heatmap, 3D geometry + point-cloud preview (Three.js / react-three-fiber).
4. Wire to the public API at `lidar.hankell.com.br` (or relative proxy).
5. Smoke tests: build passes, key screens render against a seeded store.

### P3 — Standardize error envelope everywhere (G3, Medium)
1. Replace remaining `HTTPException` raises (sensors, scenarios, reports, datasheets, simulations) with `ApiError(…, code=…)`.
2. Add an `Exception` fallback handler so unexpected errors also emit the §25 envelope (INTERNAL_ERROR).
3. Contract tests: every 4xx path returns `{error:{code,message,field,details}}` with the expected code.

### P4 — Async simulation job + progress (G4, Medium)
1. Run the long Monte Carlo in `BackgroundTasks` (FastAPI) so POST returns 202 immediately and `GET /simulations/{id}` reports live progress/trials_completed.
2. Optionally add a WebSocket `/api/simulations/{id}/ws` for live progress (§59 allows WS or async status).
3. Tests: POST returns before completion; poll converges to completed; cancel path (new `cancelled` handling).

### P5 — Angular measurement in sim path (G5, Low-Medium)
1. Surface `angular_bias` / `angular_sigma` from the sensor's `accuracy`/`precision` into the measurement-model construction in `simulations.py`.
2. Propagate angular error into az/el of detections.
3. Tests: nonzero angular sigma perturbs az/el; determinism with seed.

### P6 — Align §39 defaults (G6, Low)
1. Change default `sigma_R_threshold` to 0.05 (PRD characterization example) in `monte_carlo.py` and `analysis.py::classify`.
2. Keep editable; update tests that assume 0.1.
3. Add an explicit test locking the default to the PRD value.

### P7 — Detection-model registry by id (G7, Low-Medium)
1. Add a named detection-model registry (`api/detection_registry.py`) mapping `detection_model_id` → `DetectionModel` object.
2. `POST /api/simulations` resolves `detection_model_id` from the registry (with 404/422 if unknown) instead of always falling back.
3. Tests: registered factory model selected; unknown id → 422; `source`/`variables` populated per PRD §66.

### P8 — README + docs (G8, Low)
1. Write `README.md` (install, run, API overview, phase status).
2. Update `PROGRESS.md` to mark Phases 11-13 as started/completed as each lands; close the open gap lines.

### Acceptance / definition of done
- Each P-item lands with focused tests; **full suite must remain green** after each.
- For P1/P3 the gap-closing tests (persistence roundtrip, uniform error envelope) are required, not optional.
- Update `docs/engineering-decisions.md` for any new ambiguities discovered.

---

## 15. Bottom line

The **analysis/simulation engine and the REST API (Phases 1-10, 13-14) are essentially complete and well-tested (245 green)** — the scientific core, the rule constraints (esp. Rule 8 insufficient-data), immutable in-memory sensor versioning, all three simulation modes, sweeps, comparison, suitability, and reporting are all working and verified.

The two **high-impact gaps** are **G1 (no disk persistence — data is lost on restart)** and **G2 (no frontend/visualization — API-only)**. Both are the PRD's own "pending" Phases (10+ and 11-12). Priorities P1 and P2 above are the natural next increments; P3-P7 are smaller compliance/robustness tightenings that close the remaining contract and spec drift.**

Sources: live code under `backend/`, `PROGRESS.md`, `CONVENTIONS.md`, `docs/engineering-decisions.md` (D001-D025), PRD §1-§83, SCHEMAS §1-§40.