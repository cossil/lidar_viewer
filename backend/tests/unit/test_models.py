"""Domain model contract tests.

Covers:
  1) sensor matching PRD section 9 example validates
  2) scenario validates
  3) simulation validates
  4) results validates
  5) unknown beam_divergence round-trip
  6) simulation defaults
  7) full sensor dict validates against sensor.json schema
  8) full scenario / results validate against schemas
  9) bad reflectivity rejected
  10) bad DBH rejected
"""

from __future__ import annotations

import json
import math
import pytest

from lidar_analysis.models.common import (
    DataOrigin,
    ParameterStatus,
    SensorType,
    SimulationMode,
    JobStatus,
    ValidationStatus,
    ConfidenceLevel,
    ErrorDefinition,
    Suitability,
)
from lidar_analysis.models.parameter import Parameter
from lidar_analysis.models.provenance import Provenance
from lidar_analysis.models.sensor import (
    Range,
    RangeCurve,
    Accuracy,
    Precision,
    Angular,
    Beam,
    Scan,
    Optical,
    Assumption,
    DetectionModelReference,
    Validation,
    Sensor,
)
from lidar_analysis.models.detection_model import DetectionModel, Validity
from lidar_analysis.models.scenario import (
    Orientation,
    Pose,
    Target,
    Environment,
    Randomization,
    Scenario,
)
from lidar_analysis.models.simulation import (
    MonteCarlo,
    Criterion,
    CharacterizationCriterion,
    DetectionCriteria,
    MeasurementModel,
    SimulationAssumption,
    Simulation,
)
from lidar_analysis.models.results import (
    Metrics,
    EffectiveRanges,
    ModelConfidence,
    Distribution,
    Sweep,
    Point,
    PointCloud,
    Results,
)
from lidar_analysis.models.application_profile import (
    ApplicationProfile,
    TargetSpec,
    OperationalRange,
    Requirements,
    CriterionResult,
    SuitabilityResult,
)
from lidar_analysis.models.schemas import SCHEMAS, validate_json_schema


# ── helper: minimal provenance for SOURCE-origin parameters ──

def _prov() -> dict:
    return Provenance(
        origin=DataOrigin.SOURCE,
        user_validated=False,
    ).model_dump(mode="json", exclude_none=True)


def _param(value: float, unit: str, origin: DataOrigin = DataOrigin.SOURCE) -> dict:
    return Parameter(
        value=value, unit=unit, origin=origin,
    ).model_dump(mode="json", exclude_none=True)


# ════════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════════

@pytest.fixture()
def sensor_dict():
    """Full sensor matching the PRD section 9 structure."""
    return {
        "sensor_id": "example_sensor",
        "manufacturer": "Example",
        "model": "Example-100",
        "version": "1.0",
        "sensor_type": "mechanical_spinning",
        "range": {
            "minimum": _param(0.5, "m"),
            "maximum": _param(70.0, "m"),
            "reflectivity_curves": [],
        },
        "accuracy": {
            "range": _param(0.02, "m"),
            "definition": "1sigma",
        },
        "precision": {
            "range": _param(0.01, "m"),
            "definition": "1sigma",
        },
        "angular": {
            "horizontal_fov": _param(math.radians(360), "rad"),
            "vertical_fov": _param(math.radians(30), "rad"),
            "horizontal_resolution": _param(math.radians(0.1), "rad"),
            "vertical_resolution": _param(math.radians(0.33), "rad"),
        },
        "beam": {
            "horizontal_divergence": _param(math.radians(0.003), "rad"),
            "vertical_divergence": _param(math.radians(0.003), "rad"),
            "beam_shape": "gaussian",
        },
        "scan": {
            "type": "mechanical_spinning",
            "point_rate": _param(300000, "Hz"),
            "frame_rate": _param(10, "Hz"),
            "rotation_frequency": _param(10, "Hz"),
        },
        "optical": {
            "wavelength": _param(905e-9, "m"),
        },
        "detection": {
            "default_model": "datasheet",
        },
        "provenance": [_prov()],
        "assumptions": [],
        "validation": {
            "status": "unvalidated",
        },
    }


@pytest.fixture()
def sensor(sensor_dict):
    return Sensor(**sensor_dict)


@pytest.fixture()
def scenario_dict(sensor_dict):
    return {
        "scenario_id": "tree_10cm_30m",
        "name": "10cm tree at 30m",
        "sensor_id": sensor_dict["sensor_id"],
        "sensor_pose": {
            "position": [0.0, 0.0, 0.0],
            "orientation": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
        },
        "target": {
            "type": "cylinder",
            "position": [30.0, 0.0, 0.0],
            "orientation": [0.0, 0.0, 1.0],
            "diameter": 0.10,
            "reflectivity": 0.30,
        },
        "environment": {
            "atmosphere": "clear",
            "rain": False,
            "fog": False,
            "dust": False,
            "vegetation_occlusion": False,
            "terrain_occlusion": False,
        },
    }


@pytest.fixture()
def scenario(scenario_dict):
    return Scenario(**scenario_dict)


@pytest.fixture()
def simulation_dict(scenario_dict):
    return {
        "simulation_id": "sim_001",
        "scenario_id": scenario_dict["scenario_id"],
        "sensor_id": scenario_dict["sensor_id"],
        "sensor_version": "1.0",
        "mode": "monte_carlo",
        "duration": 1.0,
        "monte_carlo": {
            "enabled": True,
            "trials": 10000,
            "random_seed": 123456,
        },
        "detection_model_id": "analytical_v1",
        "measurement_model": {
            "range_bias": 0.0,
            "range_sigma": 0.02,
            "range_error_definition": "1sigma",
            "angular_bias": 0.0,
        },
        "detection_criteria": {
            "detected": {"minimum_returns": 1, "minimum_probability": 0.5},
            "reliable": {"minimum_returns": 5, "minimum_probability": 0.9},
            "characterized": {
                "minimum_returns": 10,
                "minimum_probability": 0.9,
                "minimum_coverage": 0.3,
                "maximum_range_uncertainty": 0.05,
            },
        },
        "software_version": "0.1.0",
        "model_version": "0.1.0",
        "status": "completed",
    }


@pytest.fixture()
def simulation(simulation_dict):
    return Simulation(**simulation_dict)


@pytest.fixture()
def results_dict():
    return {
        "simulation_id": "sim_001",
        "status": "completed",
        "metrics": {
            "detection_probability": 0.91,
            "reliable_probability": 0.87,
            "characterization_probability": 0.61,
            "expected_target_returns": 8.2,
            "geometric_coverage": 0.42,
            "target_angular_size": 0.00333,
            "beam_footprint": 0.015,
            "incidence_angle": 0.0,
            "range_uncertainty": 0.02,
        },
        "effective_ranges": {
            "detection": 37.0,
            "reliable": 31.0,
            "characterization": 24.0,
        },
        "model_confidence": {
            "physical_model": "moderate",
            "detection_model": "moderate",
            "monte_carlo_precision": "high",
        },
        "warnings": [],
    }


@pytest.fixture()
def results(results_dict):
    return Results(**results_dict)


# ════════════════════════════════════════════════════════════════
# TESTS
# ════════════════════════════════════════════════════════════════

class TestSensor:
    def test_prd_section9_example_validates(self, sensor):
        """PRD section 9 example structure creates a valid Sensor."""
        assert sensor.sensor_id == "example_sensor"
        assert sensor.manufacturer == "Example"
        assert sensor.model == "Example-100"
        assert sensor.version == "1.0"
        assert sensor.sensor_type == SensorType.MECHANICAL_SPINNING
        assert sensor.range.maximum.value == 70.0
        assert sensor.scan.type == sensor.sensor_type

    def test_full_sensor_dict_validates_schema(self, sensor, sensor_dict):
        """Full sensor dict validates against sensor.json schema."""
        d = sensor.model_dump(mode="json", exclude_none=True)
        errors = validate_json_schema(d, "sensor.json")
        assert errors == [], f"Schema errors: {errors}"

    def test_sensor_type_must_match_scan_type(self, sensor_dict):
        """Sensor with mismatched sensor_type/scan.type rejected."""
        sensor_dict["scan"]["type"] = "structured_raster"
        with pytest.raises(ValueError, match="sensor_type must match scan.type"):
            Sensor(**sensor_dict)

    def test_sensor_id_pattern(self, sensor_dict):
        """sensor_id must match [a-zA-Z0-9_-]+."""
        sensor_dict["sensor_id"] = "bad id!"
        with pytest.raises(Exception):
            Sensor(**sensor_dict)

    def test_extra_field_rejected(self, sensor_dict):
        """extra='forbid' rejects unknown fields."""
        sensor_dict["extra_junk"] = True
        with pytest.raises(Exception):
            Sensor(**sensor_dict)


class TestScenario:
    def test_scenario_validates(self, scenario):
        assert scenario.scenario_id == "tree_10cm_30m"
        assert scenario.target.type == "cylinder"
        assert scenario.target.reflectivity == pytest.approx(0.30)
        assert scenario.environment.atmosphere == "clear"

    def test_scenario_dict_validates_schema(self, scenario, scenario_dict):
        d = scenario.model_dump(mode="json", exclude_none=True)
        errors = validate_json_schema(d, "scenario.json")
        assert errors == [], f"Schema errors: {errors}"

    def test_pitch_clamp(self, scenario_dict):
        """Pitch beyond +/- pi/2 is rejected."""
        scenario_dict["sensor_pose"]["orientation"]["pitch"] = 2.0
        with pytest.raises(ValueError, match="pitch"):
            Scenario(**scenario_dict)


class TestSimulation:
    def test_simulation_validates(self, simulation):
        assert simulation.simulation_id == "sim_001"
        assert simulation.mode == SimulationMode.MONTE_CARLO
        assert simulation.duration == pytest.approx(1.0)
        assert simulation.status == JobStatus.COMPLETED

    def test_simulation_defaults(self):
        """Defaults: monte_carlo.trials==10000, random_seed==123456."""
        sim = Simulation(
            simulation_id="s1",
            scenario_id="sc1",
            sensor_id="se1",
            mode="analytical",
            duration=1.0,
            monte_carlo=MonteCarlo(enabled=False),
        )
        assert sim.monte_carlo.trials == 10000
        assert sim.random_seed == 123456

    def test_simulation_dict_validates_schema(self, simulation, simulation_dict):
        d = simulation.model_dump(mode="json", exclude_none=True)
        errors = validate_json_schema(d, "simulation.json")
        assert errors == [], f"Schema errors: {errors}"

    def test_duration_must_be_positive(self, simulation_dict):
        simulation_dict["duration"] = 0.0
        with pytest.raises(Exception):
            Simulation(**simulation_dict)

    def test_mc_trials_range(self, simulation_dict):
        simulation_dict["monte_carlo"]["trials"] = 200000
        with pytest.raises(Exception):
            Simulation(**simulation_dict)


class TestResults:
    def test_results_validates(self, results):
        assert results.simulation_id == "sim_001"
        assert results.status == "completed"
        assert results.metrics.detection_probability == pytest.approx(0.91)
        assert results.model_confidence.physical_model == ConfidenceLevel.MODERATE

    def test_results_dict_validates_schema(self, results, results_dict):
        d = results.model_dump(mode="json", exclude_none=True)
        errors = validate_json_schema(d, "results.json")
        assert errors == [], f"Schema errors: {errors}"


class TestUnknownParameter:
    def test_unknown_beam_divergence_roundtrip(self):
        """Unknown beam divergence (value=None, status=unknown) round-trips."""
        p = Parameter(
            value=None,
            unit=None,
            origin=DataOrigin.SOURCE,
            status=ParameterStatus.UNKNOWN,
        )
        assert p.value is None
        assert p.status == ParameterStatus.UNKNOWN
        dumped = p.model_dump(mode="json")
        assert dumped["value"] is None
        assert dumped["status"] == "unknown"
        restored = Parameter(**dumped)
        assert restored.value is None
        assert restored.status == ParameterStatus.UNKNOWN

    def test_unknown_status_requires_none_value(self):
        """status='unknown' with a non-None value is rejected."""
        with pytest.raises(ValueError, match="unknown.*value"):
            Parameter(value=0.003, unit="rad", origin=DataOrigin.SOURCE, status=ParameterStatus.UNKNOWN)

    def test_known_requires_value(self):
        """status='known' with value=None is rejected."""
        with pytest.raises(ValueError, match="known.*numeric"):
            Parameter(value=None, unit="m", origin=DataOrigin.SOURCE, status=ParameterStatus.KNOWN)


class TestBoundsValidation:
    def test_bad_reflectivity_rejected(self, scenario_dict):
        """Reflectivity outside [0.1, 1.0] is rejected."""
        scenario_dict["target"]["reflectivity"] = 0.05
        with pytest.raises(Exception):
            Scenario(**scenario_dict)

        scenario_dict["target"]["reflectivity"] = 1.5
        with pytest.raises(Exception):
            Scenario(**scenario_dict)

    def test_bad_dbh_rejected(self, scenario_dict):
        """Diameter outside [0.05, 1.0] is rejected."""
        scenario_dict["target"]["diameter"] = 0.01
        with pytest.raises(Exception):
            Scenario(**scenario_dict)

        scenario_dict["target"]["diameter"] = 2.0
        with pytest.raises(Exception):
            Scenario(**scenario_dict)


class TestDetectionModel:
    def test_detection_model_validates(self):
        dm = DetectionModel(
            model_id="analytical_v1",
            model_type="analytical",
            version="1.0",
            description="Range-based analytical model",
            parameters={"max_range": 70},
            required_inputs=["range", "reflectivity"],
        )
        assert dm.output == "probability"
        assert dm.confidence is None


class TestApplicationProfile:
    def test_profile_validates(self):
        p = ApplicationProfile(
            profile_id="forest_inventory_default",
            name="Forest Inventory",
            target=TargetSpec(minimum_dbh=0.05, maximum_dbh=1.0),
            operational_range=OperationalRange(minimum=0, maximum=30),
            requirements=Requirements(
                minimum_detection_probability=0.95,
                minimum_reliable_probability=0.90,
                minimum_coverage=0.30,
                maximum_range_uncertainty=0.05,
            ),
        )
        assert p.profile_id == "forest_inventory_default"

    def test_suitability_result_validates(self):
        sr = SuitabilityResult(
            classification=Suitability.CONDITIONALLY_SUITABLE,
            criteria=[
                CriterionResult(criterion="detection_probability", required=0.95, measured=0.97, passed=True),
                CriterionResult(criterion="reliable_probability", required=0.90, measured=0.84, passed=False),
            ],
            limitations=["Reliable characterization requirement not satisfied."],
        )
        assert sr.classification == Suitability.CONDITIONALLY_SUITABLE
        assert len(sr.criteria) == 2


class TestProvenance:
    def test_provenance_validates(self):
        p = Provenance(
            origin=DataOrigin.SOURCE,
            user_validated=False,
            document="sensor_datasheet.pdf",
            page=7,
            section="Performance",
            confidence=0.91,
            extraction_method="ai",
        )
        assert p.origin == DataOrigin.SOURCE
        assert p.page == 7

    def test_provenance_confidence_bounds(self):
        with pytest.raises(Exception):
            Provenance(origin=DataOrigin.SOURCE, user_validated=False, confidence=1.5)


class TestEnumValues:
    def test_all_enums_serialise_to_spec_values(self):
        """All enum values match the exact strings from the SCHEMAS spec."""
        assert DataOrigin.SOURCE.value == "SOURCE"
        assert DataOrigin.EMPIRICAL.value == "EMPIRICAL"
        assert ParameterStatus.UNKNOWN.value == "unknown"
        assert ParameterStatus.NOT_APPLICABLE.value == "not_applicable"
        assert ErrorDefinition.ONE_SIGMA.value == "1sigma"
        assert ErrorDefinition.PERCENT_95.value == "95_percent"
        assert SensorType.MECHANICAL_SPINNING.value == "mechanical_spinning"
        assert SimulationMode.MONTE_CARLO.value == "monte_carlo"
        assert JobStatus.QUEUED.value == "queued"
        assert ValidationStatus.UNVALIDATED.value == "unvalidated"
        assert Suitability.CONDITIONALLY_SUITABLE.value == "conditionally_suitable"
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.INSUFFICIENT.value == "insufficient"


class TestSchemasLoaded:
    def test_schemas_dict_populated(self):
        assert len(SCHEMAS) == 9
        assert "sensor.json" in SCHEMAS
        assert "scenario.json" in SCHEMAS
        assert "simulation.json" in SCHEMAS
        assert "results.json" in SCHEMAS

    def test_provenance_schema_structure(self):
        s = SCHEMAS["provenance.json"]
        assert s["title"] == "Provenance"
        assert "origin" in s["properties"]
        assert "user_validated" in s["properties"]
        assert s["additionalProperties"] is False

    def test_parameter_schema_structure(self):
        s = SCHEMAS["parameter.json"]
        assert s["title"] == "Parameter"
        assert "value" in s["properties"]
        assert "origin" in s["properties"]