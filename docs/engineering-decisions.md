# Engineering Decisions & Spec-Ambiguity Resolutions

Append-only. Each entry links to the PRD/SCHEMAS section that was ambiguous and how we resolved it, so builders and critics don't re-litigate. If you disagree, patch here explicitly with rationale and update affected tests.



## D001 - Coordinate convention (geometry/scanning)
PRD §14 defines right-handed world frame but no orientation convention. We adopt:
- World: LiDAR forward = +X, up = +Z, right = +Y (right-handed: Z=X cross Y? verify: +X forward, +Y right, +Z up; cross(X,Y)=XåY=(0,0,1)=Z ✓). All rotations by R=Rz(yaw)@Ry(pitch)@Rx(roll( radians; yaw around +Z, pitch around +Y.
- Range/azimuth: azimuth 0 = pointing along +X, measurement plane  XY; elevation measured from horizon toward +Z; dir=(cos(az)cos(el),sin(az)cos(el ,),sin(el)). (scanning/base.py.

## D002 - Divide divergences
PRD §10.6 distinguishes horizontal_divergence / vertical_divergence; beam shape may be elliptical. For cylindrical trunk overlap we use a single effective full-angle divergence: if only horizontal_divergence present use it; else beam.horizontal_divergence;; if axisymmetric use either. We do NOT average two values silently — if both present and differ, selection is an explicit ASSUMED parameter recorded in assumptions registry. (fallback only when user selects a mode.

## D003 - Unknown handling in parameter objects
Parameter.value may be null ONLY when status == "unknown" (SCHEMAS §4; PRD §5.4. `not_applicable` may also carry null value. The Parameter validator enforces: status in {unknown,not_applicable} → value must be None; status known/estimated → numeric value required. Never substitute zero.,

## D004 - Detection model selection & insufficient data
Detection is layered per PRD §30 priority: empirical > user calibration > datasheet envelope > analytical > assumption. A curated AnalyticalDetectionModel (the physics-inspired one) requires: beam divergence known, reflectivity known, incidence known, range known. If any REQUIRED input of the SELECTED model has status unknown → return INSUFFICIENT_DATA (SCHEMAS §27, business rule 8; PRD §32) — NOT a fabricated probability. Geometric/optical quantities NOT gated (angular size, beam footprint, expected opportunities, uncertainty、仍 computed.

## D005 - Candidate-ray model
Scan duration T and MC trials N are independent (PRD §24,: each MC trial simulates ONE physical scan of duration T( = a fresh realization of uncertainty(; scan phase randomization allowed per randomization flags. Number of candidate rays per trial comes from the actual angular sampling over T, never points_per_sec*T alone (PRD §20.,

## D006 - Point cloud semantics
A detected return yields one simulated point(per SCHEMAS point.json; fields per PRD §52,. Synthetic point cloud = combination of detected points across trials (trial_id distinguishes.; measured_range=true range+bias+noise. az/el recorded from the candidate ray. detection_probability of that ray recorded.,

## D007 - Overlap model G
G joint-occupancy fraction of a circular beam spot covered by the target's visible chord at the aim point: G= min(1, chord_width/beam_diameter( was adopted as engineering approximation (PRD §26 allows MVP analytical approx.( Documented. Chord width on a cylinder measured perpendicular to the ray (looks like a flat strip of width = projected chord. Good for beam vs small cylinder.,

## D008 - Hardware/persistence layout
data/sensors, data/scenarios, data/simulations, data/reports hold JSON files (PRD §55-57; SCHEMAS §33-34(. Sensor files named `<sensor_id>.v<version>.json` with a small index `<sensor_id>.latest` pointer => immutable versions per PRD §72/SCHEMAS rule 9. Simulations store BOTH the Simulation objectibility and the Results (immutable. Soft-delete: DELETE marks deleted=true in a sidecar (не гbing the file; remains referenced.,

## D009 - Report formats
Report sections per PRD §83; CSV for numerical sweep/results; JSON for sensor/scenario/simulation/result objects напрямую (SCHEMAS §? PRD §60. Markdown report includes provenance & assumptions optionally (PRD §83.,

## D010 - Time stamps in scanning
t_stamps are absolute seconds within [start,end](; mechanisms: spinning advances with rotation count and azimuth bins; raster advances per frame; non_repetitive parametrized continuous-time curves. `generate_rays(start_time,end_time,rng)` returns dirs (N,3), meta dict with arrays azimuth,elevation,t_stamps(and channel_index( uniform lengths N.,

## D011 - Randomness
Single top-level RNG per trial seeded from (seed,trial_index( via numpy.random.default_rng((seed+hash(trial(…. Reproducible identical to SCHEMAS §36. Simulation records random_seed. detection Bernoulli via rng.random(); measurement noise per rng.normal.,

## D012 - 'sensor_version' immutability
Put on an existing validated sensor bumps version (e.g.1.0->1.1( and writes a NEW file; old file untouched (PRD §72; SCHEMAS PUT /sensors semantics "creates a new sensor version or explicitly modifies"... wir prefer new-version.,

## D013 - Effective range definition
Effective range = largest distance in a sweep at which classification criterion first fails? PRD §42: maximum distance satisfying criterion. In sweeps the detection/reliable/characterization ranges are computed per-criterion as the max distance where the relevant P(detection/reliable/characterization) passes its configured probability&returns thresholds.,

## D014 - Search/heuristics for 'incidence angle' scenario param
SCHEMAS scenario.target has NO explicit incidence_angle field; incidence is DERIVED from target orientation + sensor pose at the hit. The compare API takes incidence_angle as a scenario-level hint: when set, builder orients the target so that the center-ray incidence equals that angle (used only by the compare convenience API; stored derived.,

## D015 - Suitability assessment
ApplicationProfile(forest_inventory_default, PRD §46/SCHEMAS §10) uses measurable criteria mapped 1:1 to results.metrics: detection_probability >= 0.95, reliable_probability >=  ‎0.90, geometric_coverage >= 0.30, range_uncertainty <= 0.05 m. Any required metric missing/insufficient → insufficient_data. All others pass → suitable; 1-2 fail → conditionally_suitable; more → not_suitable. Traceability: the report lists每 criterion required vs measured vs passed. (PRD §46; §85.,

## D016 - Numerical precision presentation
Store full IEEE floats in JSON/results; format for UI display only (per-confidence rounding,, PRD §70. Never round stored data.,

## D017 - Wavelength duplicate
SCHEMAS sensor has BOTH top-level wavelength AND optical.wavelength. Both may exist; optical.wavelength is canonical for the optical submodel; top-level mirrors it when present (kept for schema compat.; documented.,

## D018 - Spinning point_rate cap
point_rate (pts/s( is a cap; when set, candidate azimuth bins(in a rotation( are thinned (deterministically, evenly) so the emitted point rate does not exceed the cap over一 rotation; without it, point rate = channels × bins_per_rotation × rotation_freq. Documented in scanning/spinning.py.,

## D019 - Effective area for return strength
A_eff = the target's visible projected area intersected by the (maybe divergent( beam spot at the aim point; approximated as min(beam spot area, target chord strip area( ≈ min(pi*(beam_diameter/2)^2,* chord_width*segment_length( with segment_length = a fixed characteristic axial extent (scenario target height limited to beam tall?; we take segment_length = min(target_height, beam_diameter( when beam circular; compute the aligned ellipse strip width W=chord*segment; A_eff=min(pi*(d/2)^2, W(. Deterministic; documented.,

## D020 - Detection classifications (defaults
detected: N>=1 and P_detection>=0.5 (optional per schema; we treat as required minimum by default; reliable: P(N>=5>=0.90; characterized: P(N>=10>=0.90 and C_g>=0.30 and sigma_R<=0.05 (PRD §39; SCHEMAS detectionCriteria defaults example.; ALL thresholds editable.,

## D021 - 'incidence angle' const for results
results.metrics.incidence_angle is the mean incidence of the (expected( center-ray intersection measured in radians (,0..pi/2.( SCHEMAS bounds <= pi/2.,

## D022 - Angular uncertainty contribution to range
Not directly used for range; angular error perturbs the reported azimuth/elevation when angular_sigma known; range_sigma sets range noise. If angular error definition present but no sigma value → unknown; does not fabricate.,

## D023 - Range uncertainty metric
results.metrics.range_uncertainty = range_sigma when known (after converting definition to 1-sigma equivalent per PRD §34: treat published value per its stated definition; e.g. 2sigma -> sigma=value/2; 95% -> /1.96; rms -> as-is; maximum -> /3( conservative heuristic documented as ASSUMED when used); unspecified -> unknown null; never assumed 1sigma.,

## D024 - API versioning
All endpoints under /api/v1 (SCHEMAS §12,§28.. OpenAPI served at /openapi.json. Breaking change -> /api/v2.,

## D025 - Datasheet extraction is non-fabricating
Extractor uses regex/unit-aware parsers + optional AI hints; every produced parameter carries provenance(document cannot be fabricated; page/section null when unknown,. Output is a Sensor-CANDIDATE with validation.status=unvalidated,and per-param provenance. PRD §11-12] + SCHEMAS §14. Warnings list un-identified required params.,