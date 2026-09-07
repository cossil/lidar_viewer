# Product Requirements Document
## LiDAR Performance Analysis & Simulation Platform

**Document Version:** 1.0  
**Status:** Engineering Baseline  
**Primary Use:** Personal engineering research and sensor selection  
**Application Type:** Local web application  
**Primary Domain:** LiDAR performance analysis, stochastic simulation, sensor comparison, forest-inventory suitability

---

# 1. Executive Summary

This project is a local engineering application for analyzing, comparing, and simulating the performance of LiDAR sensors using manufacturer datasheets, user-defined sensor parameters, analytical models, Monte Carlo simulation, and synthetic point-cloud generation.

The primary engineering use case is evaluating whether a particular LiDAR sensor is appropriate for applications such as terrestrial and aerial forest inventory, especially the detection and characterization of small cylindrical targets such as tree trunks under controlled conditions.

The application shall answer questions such as:

- Can LiDAR A detect a 10 cm DBH tree at 30 m?
- What is the maximum detection distance for a 10 cm trunk?
- How does LiDAR A compare with LiDAR B under identical conditions?
- How many LiDAR returns should intersect a trunk during a 1-second scan?
- What is the probability of detecting the trunk?
- At what distance does reliable characterization cease to be possible?
- How does performance change with DBH, reflectivity, incidence angle, and scan duration?
- Is a particular sensor suitable for a defined forest-inventory application profile?

The application is **not intended initially to be a full electromagnetic, optical, waveform, or photonic LiDAR simulator**.

Instead, the MVP shall implement a transparent, layered engineering model:

> Sensor Model → Scenario → Scan Pattern → Ray Geometry → Target Intersection → Beam/Target Interaction → Return Strength → Detection Probability → Stochastic Returns → Measurement Error → Point Cloud → Statistical Analysis

The system must explicitly distinguish:

- manufacturer-supplied data,
- user-entered data,
- derived quantities,
- engineering assumptions,
- analytical model outputs,
- Monte Carlo results,
- empirical calibration data.

The application shall prioritize **traceability, reproducibility, model transparency, and avoidance of false precision**.

---

# 2. Problem Statement

LiDAR manufacturers publish specifications such as:

- maximum range,
- minimum range,
- accuracy,
- precision,
- angular resolution,
- field of view,
- scan rate,
- point rate,
- beam divergence,
- reflectivity-dependent range,
- wavelength,
- number of channels,
- scanning frequency.

However, these specifications do not directly answer application-specific engineering questions.

For example:

> "The LiDAR has a 70 m maximum range."

does not establish that:

> "The LiDAR can reliably detect a 10 cm tree trunk at 30 m."

A small target occupies only a fraction of the LiDAR's angular field, and actual performance depends on:

- target angular size,
- scan pattern,
- beam divergence,
- beam/target overlap,
- reflectivity,
- incidence angle,
- range,
- measurement uncertainty,
- detection probability,
- scan duration,
- target geometry,
- sensor-specific detection characteristics.

The proposed application converts manufacturer-level specifications into application-level performance estimates.

---

# 3. Product Goals

## 3.1 Primary Goals

The system shall:

1. Import LiDAR datasheets.
2. Extract sensor specifications using AI-assisted document analysis.
3. Preserve provenance for every extracted parameter.
4. Allow the user to validate and modify extracted specifications.
5. Store validated sensor specifications as JSON.
6. Define controlled simulation scenarios.
7. Model LiDAR scan patterns explicitly.
8. Model target geometry explicitly.
9. Calculate target angular size.
10. Calculate ray/target intersection.
11. Calculate incidence angle.
12. Model beam footprint and target overlap.
13. Estimate return strength.
14. Estimate or model detection probability.
15. Generate stochastic target returns.
16. Model range and angular measurement uncertainty.
17. Execute Monte Carlo simulations.
18. Generate synthetic point clouds.
19. Calculate detection, reliability, characterization, and coverage metrics.
20. Perform distance and DBH sweeps.
21. Compare multiple sensors under identical conditions.
22. Generate 2D and 3D visualizations.
23. Export numerical results.
24. Generate engineering reports.
25. Evaluate application suitability using configurable criteria.

---

# 4. Non-Goals

The MVP shall not attempt to provide:

- full Maxwell-equation electromagnetic simulation;
- photon-level optical simulation;
- proprietary internal LiDAR signal-processing replication;
- exact vendor firmware behavior;
- detailed atmospheric scattering;
- full weather simulation;
- realistic forest vegetation;
- complex bark morphology;
- branches and leaves;
- terrain occlusion;
- moving targets;
- moving LiDAR platforms;
- multipath propagation;
- waveform-level simulation;
- beam polarization modeling;
- detailed receiver electronics;
- proprietary vendor detection algorithms.

These may be future extensions.

---

# 5. Engineering Philosophy

The application shall follow these principles.

## 5.1 Transparency Over Apparent Precision

If the available information does not support a numerical estimate, the system shall explicitly report:

> Detection probability: Not reliably estimable from available data.

It shall never manufacture a probability merely because the user expects one.

---

## 5.2 Provenance Is Mandatory

Every sensor parameter must retain its source and interpretation.

Minimum provenance fields:

- parameter name;
- value;
- unit;
- source document;
- page;
- section;
- source quotation/reference where available;
- extraction method;
- source classification;
- confidence;
- user validation state;
- operating conditions.

---

## 5.3 User Validation Is Authoritative

AI extraction is advisory.

The hierarchy shall be:

> Manufacturer Document → AI Extraction → User Review → Validated Sensor Model

Once a user validates or edits a parameter, the AI must not silently change it.

---

## 5.4 Unknown Is Not Zero

Unknown values shall be represented explicitly.

Example:

```json
{
  "beam_divergence": {
    "value": null,
    "status": "unknown"
  }
}
```

The system must never silently replace unknown values with:

- zero,
- a typical value,
- a vendor-independent default,
- an inferred value.

If a fallback assumption is used, it must be explicitly selected and recorded.

---

# 6. Target Users

## Primary User

Engineering/research user performing:

- LiDAR sensor selection;
- sensor trade studies;
- robotics system design;
- forest-inventory system development;
- autonomous vehicle sensor evaluation;
- experimental planning;
- sensor characterization.

The application is intended primarily for a technically sophisticated user rather than a general consumer.

---

# 7. Primary Workflow

The normal workflow shall be:

```text
Import Datasheet
       ↓
AI Specification Extraction
       ↓
User Validation
       ↓
Save Sensor Model
       ↓
Create Simulation Scenario
       ↓
Select Sensor
       ↓
Select Target
       ↓
Configure Geometry
       ↓
Configure Scan Pattern
       ↓
Configure Simulation
       ↓
Run Analytical Analysis
       ↓
Run Monte Carlo
       ↓
Generate Point Cloud
       ↓
Analyze Results
       ↓
Compare Sensors
       ↓
Export Report
```

---

# 8. MVP Scope

## 8.1 Sensor Types

The MVP shall support generic 3D LiDAR sensors with sufficient parameters to represent:

1. Mechanical spinning LiDAR.
2. Structured/raster scanning LiDAR.
3. Non-repetitive scanning LiDAR.

The architecture shall not be tied to a specific manufacturer.

---

# 9. Sensor Data Model

Sensor models shall be stored as JSON.

A sensor definition shall contain at minimum:

```json
{
  "sensor_id": "example_sensor",
  "manufacturer": "Example",
  "model": "Example-100",
  "version": "1.0",
  "sensor_type": "mechanical_spinning",

  "range": {},
  "accuracy": {},
  "precision": {},
  "angular": {},
  "beam": {},
  "scan": {},
  "optical": {},
  "detection": {},

  "provenance": [],
  "assumptions": [],
  "validation": {}
}
```

---

# 10. Required Sensor Parameters

## 10.1 Identification

- manufacturer;
- model;
- hardware revision;
- firmware version if relevant;
- datasheet version;
- wavelength where available.

## 10.2 Range

- minimum range;
- nominal maximum range;
- maximum range by reflectivity if available;
- range conditions;
- range measurement uncertainty.

## 10.3 Accuracy

- range accuracy;
- angular accuracy;
- definition of accuracy.

The system must distinguish:

- maximum error;
- RMS;
- 1σ;
- 2σ;
- 95%;
- unspecified.

---

## 10.4 Precision

- range precision;
- angular precision;
- repeatability;
- statistical definition.

---

## 10.5 Angular Characteristics

- horizontal FOV;
- vertical FOV;
- horizontal resolution;
- vertical resolution;
- angular uncertainty;
- channel angles;
- channel count.

---

## 10.6 Beam Characteristics

Where available:

- beam divergence;
- horizontal divergence;
- vertical divergence;
- beam shape.

Unknown parameters remain unknown.

---

## 10.7 Scanning Characteristics

- scan type;
- rotation frequency;
- frame rate;
- point rate;
- channel count;
- horizontal angular resolution;
- vertical angular resolution;
- scan ordering;
- FOV;
- non-repetitive coverage behavior.

---

## 10.8 Detection Characteristics

Where available:

- detection threshold;
- range-vs-reflectivity curves;
- detection probability curves;
- minimum detectable target characteristics;
- manufacturer empirical data.

---

# 11. Datasheet Ingestion

The application shall accept:

- PDF;
- TXT;
- Markdown;
- JSON.

The ingestion pipeline shall:

1. Load the document.
2. Extract text.
3. Identify tables.
4. Identify specification sections.
5. Identify numerical values.
6. Identify units.
7. Identify operating conditions.
8. Associate values with parameters.
9. Record page and section.
10. Produce candidate sensor JSON.
11. Flag ambiguous values.
12. Present extracted values to the user.

---

# 12. AI Extraction Requirements

AI extraction shall be used for semantic interpretation, not authoritative validation.

The AI shall identify:

- parameter;
- value;
- unit;
- conditions;
- interpretation;
- confidence;
- source location.

Example:

```json
{
  "parameter": "range_accuracy",
  "value": 0.02,
  "unit": "m",
  "definition": "unspecified",
  "source": {
    "document": "sensor_datasheet.pdf",
    "page": 7,
    "section": "Performance"
  },
  "confidence": 0.91,
  "user_validated": false
}
```

The user interface shall clearly distinguish:

- AI extracted;
- user validated;
- user modified;
- derived;
- assumed.

---

# 13. Scenario Model

A scenario defines the physical conditions of one simulation.

Example:

```json
{
  "scenario_id": "tree_10cm_30m",
  "sensor_id": "example_sensor",

  "environment": {
    "atmosphere": "clear",
    "rain": false,
    "fog": false,
    "dust": false,
    "vegetation_occlusion": false
  },

  "sensor_pose": {
    "position": [0, 0, 0],
    "yaw": 0,
    "pitch": 0,
    "roll": 0
  },

  "target": {
    "type": "cylinder",
    "diameter": 0.10,
    "position": [30, 0, 0],
    "orientation": [0, 0, 1],
    "reflectivity": 0.30
  },

  "simulation": {
    "duration": 1.0,
    "monte_carlo_trials": 10000
  }
}
```

---

# 14. Coordinate System

The simulation shall use a right-handed Cartesian coordinate system.

Coordinate frames:

- World;
- LiDAR;
- Target.

The LiDAR pose shall be represented internally using:

```text
T_L =
[R  p]
[0  1]
```

where:

- R = rotation matrix;
- p = translation vector.

The user interface may expose:

- X;
- Y;
- Z;
- yaw;
- pitch;
- roll.

Internally, rotations should preferably be represented using matrices or quaternions rather than repeatedly composing Euler angles.

---

# 15. Target Models

## 15.1 Box

Parameters:

- width;
- depth;
- height;
- position;
- orientation;
- reflectivity.

Default:

```text
1 m × 1 m × 1 m
```

---

## 15.2 Tree Trunk

The MVP tree shall be an ideal cylinder.

Parameters:

- DBH;
- position;
- axis orientation;
- reflectivity.

DBH range:

```text
5 cm – 100 cm
```

Default example:

```text
10 cm
```

The MVP shall exclude:

- bark roughness;
- taper;
- branches;
- leaves;
- irregularity;
- inclination unless explicitly represented as target-axis rotation;
- surrounding vegetation.

---

# 16. Target Geometry

For a cylindrical target:

```text
r = D / 2
```

where:

- D = DBH;
- r = cylinder radius.

The target shall provide a surface normal at every intersection.

---

# 17. Ray Model

Each emitted/candidate LiDAR measurement shall be represented as:

```text
r(t) = P_L + t d
```

where:

- P_L = LiDAR position;
- d = normalized ray direction;
- t = distance parameter.

The system shall determine whether the ray intersects the target.

---

# 18. Target Intersection

## Box

Use analytical ray-box intersection.

## Cylinder

Use analytical ray-cylinder intersection.

Intersection output shall include:

- hit/miss;
- intersection position;
- true range;
- surface normal;
- surface identifier.

The geometry engine shall be independently unit-tested.

---

# 19. Target Angular Size

For a cylindrical target:

```text
θ_T = 2 atan(D / (2R))
```

Small-angle approximation:

```text
θ_T ≈ D / R
```

This metric shall be shown in the UI because it provides immediate insight into target difficulty.

Example:

A 10 cm target at 30 m has an apparent angular width of approximately:

```text
0.191°
```

---

# 20. LiDAR Scan Model

The scan model is a first-class component of the simulator.

The system shall not estimate target returns using only:

```text
points_per_second × simulation_time
```

because target intersection depends on the actual angular sampling pattern.

---

# 21. Mechanical Spinning Scanner

Parameters:

- horizontal FOV;
- vertical FOV;
- channel count;
- channel angles;
- horizontal angular resolution;
- rotation frequency;
- frame rate;
- point rate;
- scan phase.

The simulator shall generate candidate measurement directions based on the sensor's scanning geometry.

---

# 22. Structured/Raster Scanner

Parameters:

- horizontal angular step;
- vertical angular step;
- horizontal FOV;
- vertical FOV;
- scan ordering;
- frame rate;
- phase.

---

# 23. Non-Repetitive Scanner

The architecture shall support non-repetitive scan patterns.

Parameters may include:

- FOV;
- nominal point rate;
- integration time;
- empirical coverage function;
- analytical coverage model;
- scan phase.

The system shall recognize that non-repetitive sensors may progressively cover their FOV as integration time increases.

This is particularly important for sensors such as Livox-style scanners.

---

# 24. Scan Duration

Simulation duration shall be independent from Monte Carlo trial count.

Example:

```text
Physical scan:
1 second

Monte Carlo trials:
10,000
```

This means:

> Simulate the statistical distribution of possible 1-second scans 10,000 times.

It does not mean a 10,000-second scan.

---

# 25. Beam Divergence

Beam diameter at range R:

```text
d_b(R) = 2R tan(θ_b / 2)
```

Small-angle approximation:

```text
d_b(R) ≈ R θ_b
```

Beam divergence must be represented independently from angular resolution.

The application shall never assume:

```text
beam divergence = angular resolution
```

unless explicitly configured.

---

# 26. Beam/Target Overlap

Define:

```text
G ∈ [0,1]
```

where:

- 0 = no overlap;
- 1 = complete overlap.

The overlap model shall account for:

- target apparent size;
- beam footprint;
- relative geometry.

MVP may use an analytical approximation.

Future versions may implement:

- beam convolution;
- Gaussian beam model;
- explicit ray sampling;
- optical ray tracing.

---

# 27. Incidence Angle

For target surface normal n and incoming direction d:

```text
α = acos(|n · (-d)|)
```

where:

```text
0° ≤ α ≤ 90°
```

Interpretation:

- 0° = normal incidence;
- 90° = grazing incidence.

Target rotation shall therefore affect detection performance.

---

# 28. Reflectivity

Reflectivity shall be a user-configurable scenario parameter.

MVP recommended range:

```text
10% – 100%
```

The system shall preserve the manufacturer's terminology because:

> reflectivity, reflectance, albedo, target reflectivity, and range-test reflectivity are not necessarily identical physical quantities.

The UI shall display the source definition where available.

---

# 29. Return Strength Model

The MVP shall provide a simplified analytical model.

Conceptually:

```text
S ∝ ρ A_eff cos(α) / R²
```

where:

- S = received signal strength proxy;
- ρ = target reflectivity;
- A_eff = effective illuminated target area;
- α = incidence angle;
- R = range.

The implementation shall treat this as a **physics-inspired engineering approximation**, not a universal LiDAR equation.

Where manufacturer-specific empirical models exist, those models shall take precedence.

---

# 30. Detection Probability

Detection probability is defined as:

```text
P_d =
P(return detected | R, ρ, α, G, S, sensor)
```

The application shall use the highest-fidelity available model.

Priority:

1. Manufacturer empirical detection curve.
2. User experimental calibration.
3. Manufacturer range/reflectivity envelope.
4. Physics-inspired analytical model.
5. Explicit engineering assumption.

The selected model shall be recorded in simulation metadata.

---

# 31. Detection Model Confidence

Every detection result shall include:

- model type;
- model source;
- parameter confidence;
- physical-model confidence;
- whether empirical calibration exists.

Example:

```text
Detection probability: 0.87
Model: analytical
Physical model confidence: Moderate
Monte Carlo statistical precision: High
```

The application shall distinguish model confidence from numerical simulation precision.

---

# 32. Unsupported Detection Probability

If the available sensor information is insufficient to estimate detection probability credibly, the application shall report:

> Not reliably estimable from available data.

It shall not generate artificial probability values.

The system may still calculate:

- target angular size;
- beam footprint;
- expected geometric opportunities;
- theoretical sampling;
- measurement uncertainty;
- manufacturer range envelope.

---

# 33. Measurement Model

Measured range:

```text
R_m = R_t + b_R + ε_R
```

where:

- R_t = true range;
- b_R = systematic bias;
- ε_R = random error.

For Gaussian random error:

```text
ε_R ~ N(0, σ_R²)
```

The same conceptual structure shall apply to angular measurements:

```text
θ_m = θ_t + b_θ + ε_θ
```

---

# 34. Error Definition

The sensor schema shall explicitly identify the statistical definition of every uncertainty value.

Examples:

```text
1σ
2σ
95% confidence
RMS
maximum error
unspecified
```

The application shall never assume that:

```text
±2 cm = 1σ
```

unless the source explicitly states that.

---

# 35. Point Generation

Each candidate measurement follows:

```text
Candidate Ray
      ↓
Target Intersection?
      ↓
No → No target return

Yes
 ↓
True Range
 ↓
Surface Normal
 ↓
Incidence Angle
 ↓
Beam/Target Overlap
 ↓
Return Strength
 ↓
Detection Probability
 ↓
Bernoulli Trial
 ↓
Measurement Error
 ↓
Synthetic Point
```

---

# 36. Stochastic Detection

For candidate ray i:

```text
X_i ~ Bernoulli(P_d,i)
```

where:

```text
X_i = 1
```

represents a successful detected target return.

Expected target returns:

```text
E[N_T] = Σ P_d,i
```

The system shall not assume all candidate rays have identical detection probability.

---

# 37. Monte Carlo Simulation

Default:

```text
10,000 trials
```

Configurable range:

```text
1,000 – 100,000
```

Monte Carlo may vary:

- detection stochasticity;
- range error;
- angular error;
- scan phase;
- target pose uncertainty;
- target position uncertainty;
- reflectivity uncertainty;
- other explicitly enabled uncertain parameters.

Fixed user inputs shall not be randomized unless uncertainty has explicitly been defined.

---

# 38. Monte Carlo Outputs

At minimum:

- mean;
- median;
- standard deviation;
- minimum;
- maximum;
- 5th percentile;
- 25th percentile;
- 75th percentile;
- 95th percentile.

For relevant probabilities:

- probability of detection;
- probability of reliable detection;
- probability of characterization.

---

# 39. Detection Classification

The application shall support three levels.

## 39.1 DETECTED

Example default:

```text
N_target ≥ 1
```

and optionally:

```text
P_detection ≥ 50%
```

---

## 39.2 RELIABLE

Example recommended default:

```text
P(N_target ≥ 5) ≥ 90%
```

with optional geometric coverage requirement.

---

## 39.3 CHARACTERIZED

Example recommended default:

```text
P(N_target ≥ 10) ≥ 90%
```

plus:

```text
C_g ≥ 30%
```

plus:

```text
σ_R ≤ configured threshold
```

These are engineering defaults, not universal standards.

All thresholds shall be editable.

---

# 40. Geometric Coverage

Define:

```text
C_g = A_covered / A_visible
```

The system shall distinguish:

- number of points;
- point density;
- geometric coverage.

Ten points concentrated in one small area shall not be considered equivalent to ten points distributed across the target.

---

# 41. Target Sampling Density

Define:

```text
D_T = N_T / A_T
```

The application shall report:

- target return count;
- sampling density;
- point spacing;
- spatial distribution;
- clustering;
- gaps.

For cylindrical targets, returns should preferably also be analyzed in:

```text
(θ, z)
```

coordinates.

---

# 42. Effective Range

The application shall report three target-dependent ranges:

### Maximum Detection Range

Maximum distance satisfying the detection criterion.

### Maximum Reliable Range

Maximum distance satisfying the reliability criterion.

### Maximum Characterization Range

Maximum distance satisfying characterization criteria.

Normally:

```text
R_characterization
≤
R_reliable
≤
R_detection
```

These must never be confused with the manufacturer's nominal maximum range.

---

# 43. Distance Sweep

The user shall configure:

- start distance;
- end distance;
- step size.

For each distance:

```text
P_D(R)
P_R(R)
P_C(R)
E[N_T]
C_g(R)
σ_R(R)
```

shall be calculated where applicable.

---

# 44. DBH Sweep

The user shall configure:

- minimum DBH;
- maximum DBH;
- DBH increment.

MVP range:

```text
5–100 cm
```

The system shall produce:

```text
P_D = f(DBH, R)
```

and, where supported:

```text
P_R = f(DBH, R)
P_C = f(DBH, R)
```

This should be visualized as heatmaps or contour plots.

---

# 45. Sensor Comparison

Multiple sensors shall be evaluated under exactly the same:

- target;
- DBH;
- distance;
- reflectivity;
- incidence angle;
- orientation;
- duration;
- Monte Carlo count;
- classification criteria.

Only the sensor model changes.

Comparison outputs shall include:

- detection probability;
- reliable detection probability;
- characterization probability;
- expected returns;
- coverage;
- range uncertainty;
- detection range;
- reliable range;
- characterization range.

---

# 46. Forest Inventory Application Profile

The application shall support configurable application profiles.

Example:

```text
Application:
Forest Inventory

DBH:
5–100 cm

Operational distance:
0–30 m

Required detection probability:
≥95%

Reliable characterization:
≥90%

Minimum geometric coverage:
30%

Maximum range uncertainty:
5 cm
```

The application shall produce:

```text
Suitable
Conditionally Suitable
Not Suitable
Insufficient Data
```

The classification must be traceable to explicit criteria.

It shall not be generated solely by an LLM opinion.

---

# 47. User Interface

The application shall have the following primary screens.

## 47.1 Dashboard

Display:

- sensors;
- recent scenarios;
- recent simulations;
- saved reports;
- comparison studies.

---

## 47.2 Sensor Library

Functions:

- import datasheet;
- create sensor;
- edit sensor;
- validate extracted specifications;
- duplicate sensor;
- compare sensors;
- inspect provenance.

---

## 47.3 Sensor Validation Screen

Display each parameter with:

- value;
- unit;
- source;
- page;
- conditions;
- AI confidence;
- validation state.

The user shall be able to:

- accept;
- edit;
- reject;
- mark unknown.

---

# 48. Scenario Builder

Sections:

### Sensor

Select sensor model.

### Environment

- clear atmosphere;
- rain;
- fog;
- dust;
- vegetation;
- terrain.

MVP environment controls should visibly indicate unsupported future features.

### LiDAR Pose

- position;
- yaw;
- pitch;
- roll.

### Target

- type;
- dimensions;
- DBH;
- position;
- orientation;
- reflectivity.

### Simulation

- duration;
- Monte Carlo trials;
- random seed.

---

# 49. Analysis Dashboard

The analysis screen shall show:

## Primary Metrics

- detection probability;
- expected target points;
- probability of reliable detection;
- probability of characterization;
- geometric coverage;
- range uncertainty.

## Secondary Metrics

- target angular size;
- beam footprint;
- incidence angle;
- point density;
- effective ranges.

---

# 50. 2D Visualization

Required plots:

1. Detection probability vs distance.
2. Expected target returns vs distance.
3. Reliability vs distance.
4. Characterization probability vs distance.
5. Coverage vs distance.
6. Range uncertainty vs distance.
7. Detection probability vs DBH.
8. DBH-distance heatmap.
9. Detection probability vs reflectivity.
10. Detection probability vs incidence angle.

---

# 51. 3D Visualization

The application shall provide interactive 3D visualization of:

- LiDAR;
- target;
- coordinate axes;
- FOV;
- rays;
- beam footprint where modeled;
- successful returns;
- missed candidate rays where useful;
- synthetic point cloud.

User controls:

- rotate;
- pan;
- zoom;
- reset view;
- hide/show components;
- select points;
- display coordinates;
- display target surface.

---

# 52. Point Cloud Visualization

Points shall contain metadata such as:

```text
point_id
trial_id
range
true_range
range_error
azimuth
elevation
incidence_angle
detection_probability
target_surface
```

The viewer should support coloring/filtering by these attributes.

---

# 53. Reproducibility

Every simulation shall record:

- sensor model version;
- scenario;
- simulation mode;
- random seed;
- Monte Carlo count;
- software version;
- model version;
- assumptions;
- parameter provenance.

Given identical:

```text
sensor
scenario
model version
random seed
simulation settings
```

the result must be reproducible.

---

# 54. Simulation Modes

## Analytical

Purpose:

- fast evaluation;
- broad parameter sweeps;
- preliminary trade studies.

Characteristics:

- deterministic;
- fast;
- limited stochastic detail.

---

## Monte Carlo

Purpose:

- probability estimation;
- uncertainty propagation;
- reliability analysis.

---

## Synthetic Point Cloud

Purpose:

- spatial analysis;
- geometric inspection;
- visualization;
- point-distribution evaluation.

The three modes shall share the same underlying model components.

---

# 55. Software Architecture

Recommended architecture:

```text
Browser
   │
   │ HTTP / WebSocket
   ▼
Python Backend
   │
   ├── Sensor Repository
   ├── Datasheet Extraction
   ├── Simulation Engine
   ├── Analysis Engine
   └── Report Generator
```

The application shall initially run locally.

---

# 56. Recommended Technology Stack

## Frontend

Recommended:

- React;
- TypeScript;
- Vite.

Visualization:

- Plotly or equivalent;
- Three.js / React Three Fiber or equivalent.

---

## Backend

Recommended:

- Python;
- FastAPI.

Numerical computation:

- NumPy;
- SciPy;
- Pandas where useful.

Geometry:

- custom analytical geometry initially;
- optional computational geometry library where justified.

---

## Persistence

Primary sensor/scenario storage:

```text
JSON
```

No relational database is required for MVP.

---

# 57. Suggested Project Structure

```text
lidar-analysis/
│
├── frontend/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── ingestion/
│   ├── reporting/
│   │
│   └── simulation/
│       ├── geometry/
│       │   ├── coordinate_system.py
│       │   ├── transforms.py
│       │   ├── ray.py
│       │   ├── box.py
│       │   └── cylinder.py
│       │
│       ├── scanning/
│       │   ├── base.py
│       │   ├── spinning.py
│       │   ├── raster.py
│       │   └── non_repetitive.py
│       │
│       ├── optics/
│       │   ├── beam.py
│       │   ├── footprint.py
│       │   └── incidence.py
│       │
│       ├── detection/
│       │   ├── base.py
│       │   ├── datasheet.py
│       │   ├── analytical.py
│       │   └── empirical.py
│       │
│       ├── measurement/
│       │   ├── range_error.py
│       │   └── angular_error.py
│       │
│       ├── monte_carlo/
│       │   ├── engine.py
│       │   └── statistics.py
│       │
│       ├── targets/
│       │   ├── box.py
│       │   └── tree.py
│       │
│       └── analysis/
│           ├── detection.py
│           ├── coverage.py
│           ├── sweeps.py
│           └── comparison.py
│
├── data/
│   ├── sensors/
│   ├── scenarios/
│   ├── simulations/
│   └── reports/
│
├── tests/
│
└── docs/
```

The coding agent shall **not** implement the simulator as one monolithic function.

---

# 58. API Requirements

Representative API:

```text
GET    /api/sensors
POST   /api/sensors
GET    /api/sensors/{id}
PUT    /api/sensors/{id}
DELETE /api/sensors/{id}

POST   /api/datasheets/extract
POST   /api/datasheets/validate

GET    /api/scenarios
POST   /api/scenarios
GET    /api/scenarios/{id}

POST   /api/simulations
GET    /api/simulations/{id}

POST   /api/analysis/distance-sweep
POST   /api/analysis/dbh-sweep
POST   /api/analysis/compare

POST   /api/reports
GET    /api/reports/{id}
```

Long-running Monte Carlo simulations may use WebSocket or asynchronous job status.

---

# 59. Simulation Job Model

A simulation job should expose:

```text
queued
running
completed
failed
cancelled
```

Progress should be reported for large Monte Carlo runs.

Example:

```json
{
  "simulation_id": "sim_001",
  "status": "running",
  "progress": 0.63,
  "trials_completed": 6300,
  "trials_total": 10000
}
```

---

# 60. Export Requirements

The application shall support:

## CSV

For numerical simulation data.

## JSON

For:

- sensors;
- scenarios;
- simulations;
- results.

## Markdown

For engineering reports.

Reports shall include:

1. Executive summary.
2. Sensor information.
3. Scenario.
4. Target.
5. Environmental assumptions.
6. Mathematical model.
7. Detection model.
8. Simulation configuration.
9. Results.
10. Statistical analysis.
11. Limitations.
12. Assumptions.
13. Provenance.
14. Conclusions.

---

# 61. Assumption Registry

Each simulation shall store explicit assumptions.

Example:

```json
{
  "assumptions": [
    {
      "id": "A001",
      "description": "Clear atmosphere",
      "status": "active"
    },
    {
      "id": "A002",
      "description": "No vegetation occlusion",
      "status": "active"
    },
    {
      "id": "A003",
      "description": "Beam divergence unavailable; analytical fallback disabled",
      "status": "active"
    }
  ]
}
```

---

# 62. Parameter Classification

Every important value shall have a classification:

```text
SOURCE
DERIVED
ASSUMED
MODELED
SIMULATED
EMPIRICAL
USER_DEFINED
```

Example:

```text
DBH:
USER_DEFINED

Target angular size:
DERIVED

Detection probability:
MODELED

Measured range:
SIMULATED
```

---

# 63. Validation Strategy

## Level 1 — Mathematical Validation

Test:

- coordinate transforms;
- ray-plane intersection;
- ray-box intersection;
- ray-cylinder intersection;
- angular-size equation;
- incidence-angle calculation;
- beam-footprint equation.

Known analytical solutions shall be used.

---

# 64. Level 2 — Synthetic Validation

Construct idealized scenarios where expected behavior is known.

Examples:

### Ideal Target

A large flat target at normal incidence should produce returns according to the configured detection model.

### No Intersection

A ray outside the target must never generate a target return.

### Zero Probability

```text
P_d = 0
```

must produce zero target detections.

### Certain Detection

```text
P_d = 1
```

must produce detection on every intersecting candidate ray.

---

# 65. Level 3 — Experimental Validation

Future experimental validation shall use physical targets approximating cylinders.

Suggested tests:

```text
DBH:
10 cm

Distance:
10 / 20 / 30 / 40 / 50 m

Reflectivity:
measured/configured

Incidence:
0° / selected angles

Duration:
1 s or longer
```

Record:

- number of candidate opportunities;
- number of detected returns;
- measured range;
- point count;
- spatial distribution;
- reflectivity;
- incidence angle.

Empirical detection probability:

```text
P_d = N_return / N_attempt
```

Experimental data can then be used to calibrate the sensor model.

---

# 66. Empirical Calibration

The architecture shall allow a sensor to contain an empirical detection model.

Example:

```json
{
  "model_type": "empirical",
  "source": "field_test_2026_09",
  "variables": [
    "range",
    "reflectivity",
    "incidence_angle"
  ]
}
```

Empirical calibration must not overwrite the original manufacturer data.

Instead:

```text
Manufacturer Model
+
Experimental Calibration
```

shall remain traceable.

---

# 67. Performance Requirements

The application shall be responsive for ordinary analytical calculations.

Target:

- analytical single scenario: near-interactive;
- 1,000-trial Monte Carlo: interactive where practical;
- 10,000-trial Monte Carlo: preferably seconds rather than minutes for simple scenarios;
- large sweeps: asynchronous jobs.

Performance optimization should prioritize:

1. NumPy vectorization;
2. batch ray generation;
3. vectorized intersection;
4. avoiding Python loops where computationally expensive;
5. multiprocessing only after profiling.

---

# 68. Numerical Requirements

Use SI units internally.

Recommended:

```text
distance → meters
angle → radians internally
time → seconds
DBH → meters
reflectivity → normalized 0–1
probability → normalized 0–1
```

The UI may display:

- degrees;
- centimeters;
- millimeters;
- meters.

Conversions must occur at the API/model boundary.

---

# 69. Randomness

The Monte Carlo engine shall support explicit random seeds.

Example:

```text
seed = 123456
```

The simulation metadata must preserve the seed.

The application shall allow:

- automatic random seed;
- user-defined seed.

---

# 70. Numerical Precision and Presentation

The UI shall avoid false precision.

For example:

```text
87%
```

may be preferable to:

```text
87.34217%
```

when the physical model is only moderately confident.

Numerical precision shall be determined independently from model confidence.

---

# 71. Error Handling

The system shall detect:

- invalid sensor parameters;
- missing required parameters;
- invalid units;
- impossible geometries;
- negative ranges;
- DBH outside allowed range;
- invalid probabilities;
- invalid angular ranges;
- incompatible scan configurations.

Example:

```text
Error:
Beam divergence is required by the selected detection model but is
unknown for this sensor.

Choose:
[Enter value]
[Use explicit fallback model]
[Cancel simulation]
```

---

# 72. Data Integrity

Sensor versions should be immutable after validation unless explicitly edited into a new version.

Recommended:

```text
Sensor A v1.0
Sensor A v1.1
Sensor A v2.0
```

A simulation must reference the exact sensor version used.

This ensures old results remain reproducible.

---

# 73. Comparison Integrity

Sensor comparisons must use identical scenario parameters.

The application shall flag comparisons if:

- target differs;
- distance differs;
- reflectivity differs;
- duration differs;
- detection criteria differ;
- environmental assumptions differ.

---

# 74. Required MVP Questions

The completed MVP must be capable of answering:

### Question 1

> Can this LiDAR detect a 10 cm DBH tree at 30 m?

Output:

- detection probability;
- classification;
- expected returns;
- assumptions;
- model confidence.

### Question 2

> What is the maximum detection distance?

Output:

```text
Maximum Detection Range
Maximum Reliable Range
Maximum Characterization Range
```

### Question 3

> How does sensor A compare with sensor B?

Output:

comparison table and plots.

### Question 4

> How many points should hit the trunk during a 1-second scan?

Output:

- expected points;
- distribution;
- percentiles;
- point-cloud visualization.

### Question 5

> Is the sensor suitable for forest inventory?

Output:

application-profile assessment based on measurable criteria.

---

# 75. MVP Acceptance Criteria

The MVP shall not be considered complete unless all of the following are possible.

## Sensor Management

- Import a datasheet.
- Extract candidate specifications.
- Review extracted values.
- Edit values.
- Validate values.
- Save sensor as JSON.
- View provenance.

## Geometry

- Create a box.
- Create a cylindrical tree.
- Change DBH.
- Change target distance.
- Change target orientation.
- Change LiDAR orientation.
- Calculate ray intersections.

## Scan

- Simulate spinning scanner.
- Simulate structured scanner.
- Support a non-repetitive scanner abstraction.
- Simulate finite duration.

## Detection

- Configure reflectivity.
- Calculate incidence angle.
- Calculate beam footprint when divergence is available.
- Apply detection model.
- Generate stochastic returns.

## Monte Carlo

- Configure trial count.
- Configure random seed.
- Produce statistical outputs.
- Produce reproducible results.

## Analysis

- Detection probability.
- Expected point count.
- Reliability probability.
- Characterization probability.
- Geometric coverage.
- Range uncertainty.
- Distance sweep.
- DBH sweep.
- Sensor comparison.

## Visualization

- 2D plots.
- 3D target.
- 3D point cloud.
- Sensor/target geometry.

## Reporting

- Export CSV.
- Export JSON.
- Generate Markdown engineering report.

---

# 76. MVP Validity Boundary

The report must explicitly state that MVP results assume:

```text
Clear atmosphere
No rain
No fog
No dust
No snow
No vegetation occlusion
No terrain occlusion
Stationary sensor
Stationary target
Idealized target geometry
No multipath
No waveform-level effects
No proprietary firmware behavior
```

Results shall therefore be described as:

> Engineering-model predictions under the stated assumptions.

They shall not be represented as guaranteed field performance.

---

# 77. Future Development

Potential Phase 2 capabilities:

- weather attenuation;
- atmospheric transmission;
- vegetation occlusion;
- terrain;
- irregular trunks;
- bark roughness;
- trunk taper;
- branches;
- leaves;
- multiple targets;
- target clutter;
- LiDAR motion;
- vehicle motion;
- GNSS/IMU trajectories;
- sensor vibration;
- multipath;
- more advanced beam models.

---

# 78. Future Phase 3

Advanced physical modeling:

- waveform simulation;
- receiver noise;
- photon statistics;
- optical aperture;
- laser pulse energy;
- detector sensitivity;
- wavelength-dependent reflectance;
- atmospheric scattering;
- time-of-flight electronics;
- signal processing;
- detailed beam profiles.

This would transform the platform from an engineering performance analyzer into a more complete LiDAR physics simulator.

---

# 79. AI Coding Agent Instructions

The coding agent implementing this project shall follow these rules.

## Rule 1 — Do Not Invent Sensor Specifications

Never fabricate missing manufacturer parameters.

---

## Rule 2 — Preserve Provenance

Every imported sensor parameter must retain source information.

---

## Rule 3 — Never Silently Change Validated Data

User-validated sensor parameters are authoritative.

---

## Rule 4 — Explicitly Represent Unknowns

Use:

```text
null + unknown status
```

rather than zero or inferred values.

---

## Rule 5 — Separate Model Layers

Do not combine:

- geometry;
- scanning;
- optics;
- detection;
- measurement error;
- Monte Carlo;
- analysis

into one function.

---

## Rule 6 — Reproducibility

Every stochastic simulation must support deterministic reproduction through a random seed.

---

## Rule 7 — No Hidden Assumptions

Any fallback or approximation must appear in the simulation assumptions.

---

## Rule 8 — No Fake Detection Probability

If the available information does not support a probability estimate, return:

```text
Not reliably estimable from available data
```

---

## Rule 9 — Test Before Optimization

First implement mathematically correct reference implementations.

Optimize only after profiling.

---

## Rule 10 — Use SI Units Internally

Never mix centimeters, millimeters, feet, degrees, etc. inside core numerical code without explicit conversion.

---

# 80. Recommended Implementation Sequence

The AI coding agent should implement the application in the following order.

## Phase 1 — Domain Models

Implement:

- sensor schema;
- provenance;
- assumptions;
- scenario schema;
- target schema.

Do not build the UI first.

---

## Phase 2 — Geometry Engine

Implement and test:

- coordinate frames;
- transformations;
- rays;
- box intersection;
- cylinder intersection;
- surface normals;
- angular size;
- incidence angle.

---

## Phase 3 — Scan Engine

Implement:

- base scanner interface;
- spinning scanner;
- raster scanner;
- non-repetitive scanner abstraction.

---

## Phase 4 — Beam/Optical Model

Implement:

- beam divergence;
- footprint;
- target overlap;
- reflectivity;
- simplified return-strength model.

---

## Phase 5 — Detection Engine

Implement:

- base detection interface;
- datasheet model;
- analytical model;
- empirical model;
- model confidence.

---

## Phase 6 — Measurement Model

Implement:

- range bias;
- range random error;
- angular bias;
- angular random error.

---

## Phase 7 — Simulation Engine

Implement:

- candidate ray generation;
- intersection;
- detection;
- stochastic return generation;
- measurement errors;
- synthetic point cloud.

---

## Phase 8 — Monte Carlo

Implement:

- trial execution;
- random seed;
- uncertainty propagation;
- statistical analysis.

---

## Phase 9 — Analysis

Implement:

- detection;
- reliability;
- characterization;
- coverage;
- distance sweep;
- DBH sweep;
- sensor comparison.

---

## Phase 10 — Backend API

Expose the simulation and analysis engine through the REST API.

---

## Phase 11 — Frontend

Implement:

- dashboard;
- sensor library;
- sensor validation;
- scenario builder;
- simulation controls;
- results dashboard.

---

## Phase 12 — Visualization

Implement:

- 2D plots;
- heatmaps;
- 3D geometry;
- point-cloud visualization.

---

## Phase 13 — Reporting

Implement:

- CSV;
- JSON;
- Markdown report.

---

## Phase 14 — Integration Testing

Run complete end-to-end scenarios.

---

# 81. Reference End-to-End Test Case

The project shall include at least one canonical fixture.

```text
Target:
Cylinder

DBH:
10 cm

Distance:
30 m

Reflectivity:
30%

Incidence:
0°

LiDAR orientation:
Horizontal

Simulation duration:
1 second

Monte Carlo trials:
10,000

Environment:
Clear

Vegetation:
None
```

The exact numerical result is not predefined.

The purpose of the fixture is to ensure:

- deterministic execution;
- reproducibility;
- correct geometry;
- correct scan generation;
- correct statistical processing;
- stable API behavior.

---

# 82. Example Analytical Outputs

For a hypothetical sensor, the system might report:

```text
Target:
10 cm DBH

Range:
30 m

Angular size:
0.191°

Beam footprint:
[model dependent]

Incidence angle:
0°

Expected target returns:
4.8

P(detection):
82%

P(reliable):
61%

P(characterized):
34%

Range uncertainty:
2.1 cm

Classification:
Detected
```

These values are illustrative only. The application must calculate actual values from the sensor model and scenario.

---

# 83. Engineering Report Structure

Generated reports shall follow:

```text
1. Executive Summary

2. Sensor
   2.1 Manufacturer
   2.2 Model
   2.3 Specifications
   2.4 Provenance

3. Scenario
   3.1 Environment
   3.2 LiDAR Pose
   3.3 Target Geometry
   3.4 Reflectivity
   3.5 Duration

4. Mathematical Model

5. Detection Model

6. Monte Carlo Configuration

7. Results
   7.1 Detection
   7.2 Reliability
   7.3 Characterization
   7.4 Point Count
   7.5 Coverage
   7.6 Uncertainty

8. Effective Ranges

9. Sensor Comparison

10. Suitability Assessment

11. Assumptions

12. Limitations

13. Provenance

14. Reproducibility Information

15. Conclusion
```

---

# 84. Definition of Done

The project is complete when an engineer can perform the following workflow without modifying source code:

```text
Import LiDAR datasheet
        ↓
Review extracted specifications
        ↓
Validate sensor
        ↓
Create 10 cm tree
        ↓
Set distance = 30 m
        ↓
Set reflectivity
        ↓
Set incidence angle
        ↓
Set scan duration = 1 s
        ↓
Run Monte Carlo
        ↓
View detection probability
        ↓
View expected points
        ↓
View point cloud
        ↓
Sweep distance
        ↓
Determine effective ranges
        ↓
Compare another LiDAR
        ↓
Export engineering report
```

---

# 85. Final Engineering Principle

The fundamental purpose of this application is not to produce visually convincing simulated point clouds.

Its purpose is to provide an **auditable engineering framework for translating LiDAR specifications into application-level performance estimates**.

The core hierarchy is:

```text
Manufacturer Data
       ↓
Validated Sensor Model
       ↓
Physical Geometry
       ↓
Scan Geometry
       ↓
Beam/Target Interaction
       ↓
Detection Model
       ↓
Measurement Model
       ↓
Monte Carlo Simulation
       ↓
Statistical Performance
       ↓
Engineering Decision
```

Every result must be traceable backward through this chain.

The system should therefore favor:

> **transparent assumptions + explicit uncertainty + reproducibility + measurable criteria**

over:

> **complexity + apparent realism + unsupported numerical precision**

This principle governs the architecture, mathematical implementation, UI, reporting, validation strategy, and future expansion of the platform.