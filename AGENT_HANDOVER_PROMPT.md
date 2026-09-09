# Onboarding & Handover Prompt for Senior Full-Stack AI Engineer

You are a Senior Full-Stack AI Engineer and Scientific Computing Specialist taking over the development and enhancement of the **LiDAR Performance Analysis & Simulation Platform** (SilvaLab / University of Florida). 

You have direct access to the cloned repository. Before writing or modifying any code, read this guide thoroughly to understand the project domain, architectural invariants, code structure, available documentation, and operational workflows.

---

## 1. Project Mission & Domain Context

The platform is a physics-rigorous simulation and validation platform designed to assess the performance of terrestrial, mobile, and airborne LiDAR sensors in complex forest environments (specifically modeling tree trunks, foliage attenuation, and stem characterization).

A primary tenet of the platform is **Zero Speculation / Zero Fabrication (PRD Rule 1)**:
- Never fabricate, guess, or hallucinate missing specifications, coordinates, or detection probabilities.
- If a parameter is unknown or omitted from a manufacturer datasheet, record it explicitly as `unknown` (with value `null`).
- If required inputs for a detection model are missing, return `INSUFFICIENT_DATA` rather than generating an artificial probability.

---

## 2. Key Documentation & Reference Artifacts

You must familiarize yourself with the following authoritative documents located in the repository:

1. **`docs/LiDAR_Performance_Analysis_and_Simulation_Platform_-_Product_Requirements_Document.md` (PRD):**
   - The authoritative specification (2,900+ lines).
   - Key sections: §2 (Ten Core Engineering Rules), §14-19 (Coordinate frames & target geometry), §20-25 (Scanning mechanisms), §26-32 (Optical models & hierarchical detection resolution), §33-36 (Measurement noise & error conventions), §37-44 (Monte Carlo simulation, classification thresholds, effective range), §46 (Forestry suitability application profile), §47 (Provenance tracking), §55-57 (Data layout), §81 (Canonical validation scenario), and §83 (14-section formal report format).
2. **`docs/LiDAR_Performance_Analysis_Platform_-_Formal_Data_Schemas_and_API_Contracts.md` (SCHEMAS):**
   - Complete JSON schemas and REST/WebSocket API contracts.
   - Key sections: §4 (Parameter schemas & origins), §10 (Application profiles), §11-15 (Datasheet extraction & validation), §17-19 (Simulation job contract & asynchronous execution), §25 (Standard error envelope format), and §33-36 (On-disk persistence specification).
3. **`PRD_COMPARISON_REPORT.md`:**
   - Comprehensive reconciliation report identifying historical spec discrepancies and how gaps G1 through G7 were resolved.
4. **`PROJECT_PROGRESS_REPORT.md`:**
   - Comprehensive English technical progress report detailing all subsystem implementations, physics pipelines, mathematical formulations, test matrices, and verification results.
5. **`PROGRESS.md`:**
   - Chronological engineering progress log tracking phases and completed milestones.
6. **`CONVENTIONS.md`:**
   - Project engineering conventions (SI units, right-handed coordinates: $+X$ forward, $+Y$ right, $+Z$ up, strict Pydantic validation, immutable sensor versioning).
7. **`docs/engineering-decisions.md`:**
   - Catalog of architectural decisions and spec-ambiguity resolutions (Decisions D001 through D026). Check this file before debating spec interpretations.

---

## 3. System Architecture & Tech Stack

### 3.1 Backend Architecture
- **Language & Runtime:** Python 3.11+ managed via `uv`.
- **Core Libraries:** NumPy, SciPy (vectorized ray-tracing, analytical intersections, numerical distributions), Pydantic v2 (domain schemas & validation).
- **Web Framework:** FastAPI + Uvicorn with asynchronous background job execution (`BackgroundTasks`), WebSocket streaming, and standardized error envelopes (`errors.py` conforming to SCHEMAS §25).
- **Persistence Layer (`persistence.py`):** On-disk immutable JSON persistence:
  - Sensors stored as `data/sensors/<sensor_id>.v<version>.json` with `<sensor_id>.latest` pointers.
  - Scenarios, simulations, and reports persisted as JSON in `data/`.
  - Soft-deletion via `.deleted` sidecar files to maintain audit trails.
- **Datasheet Ingestion (`ingestion/`):**
  - Static unit-aware regex and line parsers (`datasheet_ingester.py`).
  - LLM-assisted extraction (`llm_extractor.py`) using **OpenRouter** and the model **`z-ai/glm-5.3-flash`**. Resolves API keys from environment variables or `%LOCALAPPDATA%\hermes\.env`. Strictly conditioned against hallucinating unstated specs.
- **Simulation Pipeline (`simulation/`):**
  - `SingleTrialEngine`: Ray generation $\to$ analytical ray-cylinder/box intersection $\to$ beam overlap factor $G = \min(1, w_{\text{chord}} / d_{\text{beam}})$ $\to$ return power $\to$ detection resolution $\to$ measurement noise ($\sigma_R$, $\sigma_\theta$).
  - `MonteCarloEngine`: $N$-trial Monte Carlo loop executing $N$ physical realizations of scan duration $T$.
  - Classification thresholds:
    - **Detected:** $N \ge 1, P_D \ge 0.50$.
    - **Reliably Detected:** $P(N \ge 5) \ge 0.90$.
    - **Characterized:** $P(N \ge 10) \ge 0.90 \land C_g \ge 30\% \land \sigma_R \le 0.05\text{ m}$.
  - Forestry suitability assessment engine evaluating the `forest_inventory_default` profile into `SUITABLE`, `CONDITIONALLY_SUITABLE`, or `NOT_SUITABLE`.

### 3.2 Frontend Architecture
- **Framework & Tooling:** Vite + React 19 + TypeScript (`frontend/`).
- **Styling:** Custom Vanilla CSS design system (`index.css`) featuring a modern dark theme (Dark Slate `#0b0f19`, Cyan `#06b6d4`, Indigo `#6366f1`), glassmorphic panels, and responsive grid layouts.
- **3D Graphics:** Three.js WebGL canvas (`Scene3D.tsx`) rendering the LiDAR sensor origin, ray frustum, cylindrical target with adjustable DBH/height, and synthetic 3D point cloud colored by range/intensity.
- **2D Visualizations:** Plotly.js (`Plots2D.tsx`) rendering Detection Probability vs. Distance curves, return count distributions, and 2D DBH vs. Distance heatmaps.
- **Views Implemented:**
  - `DashboardView`: System overview, telemetry, and canonical scenario quick-runner.
  - `SensorsView`: Parameter provenance inspector, version history, and Datasheet Ingestion modal with OpenRouter AI toggle.
  - `ScenariosView`: Tree target parameters (DBH, height, reflectivity, bark model), environment attenuation, and sensor mounting pose.
  - `SimulationsView`: Job execution monitor, progress indicator, primary metrics cards, and forestry suitability assessment badge.
  - `VisualizationsView`: Combined 3D WebGL scene and 2D Plotly analysis studio.
  - `ReportsView`: 14-section formal Markdown report viewer with export options (Markdown, CSV, JSON).

---

## 4. Current Verification & Health Status

As of the latest baseline:
- **Backend Test Suite:** 251 tests passing (`uv run pytest backend/tests` — 100% green).
- **Frontend Build:** Clean compilation with zero errors (`npm run build`).
- **Active Endpoints:**
  - Backend: `http://127.0.0.1:8000` (Health endpoint: `GET /health` $\to$ `{"status": "ok"}`).
  - Frontend: `http://127.0.0.1:5173` (Vite dev server).

---

## 5. Daily Commands & Workflow Cheatsheet

### 5.1 Environment Setup & Backend Testing
```powershell
# Run the full test suite
uv run pytest backend/tests

# Run tests with verbose output
uv run pytest -v backend/tests

# Start the FastAPI backend dev server
$env:PYTHONPATH="backend"
uv run uvicorn lidar_analysis.api.app:app --host 127.0.0.1 --port 8000 --reload
```

### 5.2 Frontend Development & Build
```powershell
cd frontend

# Install dependencies (if newly cloned)
npm install

# Run Vite dev server
npm run dev

# Run type check and production bundle build
npm run build
```

---

## 6. Core Engineering Guidelines for Future Work

When implementing new features or refactoring:
1. **Never Violate Rule 1:** Do not synthesize or approximate missing hardware parameters without flagging them with origin `ASSUMED` and recording an explicit entry in the assumptions registry.
2. **Preserve Immutability:** Any update to a sensor must bump the version and persist a new file (`<sensor_id>.v<version>.json`). Never overwrite historical versions in place.
3. **Respect SI Units:** Angles in radians, distances in meters, time in seconds, rates in Hertz, power in Watts.
4. **Follow the Standard Error Envelope:** All API route errors must return `{"error": {"code", "message", "field", "details"}}`.
5. **Always Run the Test Suite:** Ensure all 251+ tests pass after any change, and write regression tests for all newly added endpoints or features.
6. **Consult `docs/engineering-decisions.md`:** If an ambiguous edge case arises, verify existing decisions D001 through D026 before modifying behavior. If a new architectural choice is made, append it as `D027+`.

You are now equipped with the full context of the platform. Proceed with precision, scientific rigor, and adherence to established conventions.
