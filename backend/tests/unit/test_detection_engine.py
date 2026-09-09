"""Detection-engine tests: priority chain (PRD 30), empirical interpolation, rule-8.

Covers `lidar_analysis.physics.detection` resolution behavior.
"""
from __future__ import annotations

import pytest

from lidar_analysis.physics.detection import (
    AnalyticalModel, AssumptionModel, DatasheetEnvelopeModel,
    DatasheetModel, DetectionModelResolver, DetectionModelType,
    EmpiricalModel, ManufacturerCurveModel, MODEL_PRIORITY,
    SensorParamsView, insufficient_data_result, resolve_detection_model,
)

EMP_2PT = [
    (10.0 ,1.0),
    (20.0 ,0.5),
]

class TestEmpiricalInterpolation:
    def _model(self):
        return EmpiricalModel(
            points=[(10.0, 1.0), (20.0, 0.5), (30.0, 0.1)],
            reflectivity=0.5,
            source="field_trial",
        )

    def test_returns_value_at_calibration_point(self):
        m = self._model()
        r = m.compute_detection_probability(
            range_to_target=20.0, reflectivity=0.5,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0)
        assert r.probability == pytest.approx(0.5, abs=1e-9)

    def test_interpolation_between_points(self):
        m = self._model()
        r = m.compute_detection_probability(
            range_to_target=15.0, reflectivity=0.5,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0)
        assert r.probability == pytest.approx(0.75, abs=1e-9)
# clamp tests
    def test_clamp_low(self):
        m = self._model()
        r = m.compute_detection_probability(
            range_to_target=5.0, reflectivity=0.5,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0)
        assert r.probability == pytest.approx(1.0, abs=1e-9)

    def test_clamp_high(self):
        m = self._model()
        r = m.compute_detection_probability(
            range_to_target=50.0, reflectivity=0.5,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0)
        assert r.probability == pytest.approx(0.1, abs=1e-9)
# empirical metadata + reflectivity scaling

    def test_records_empirical_metadata(self):
        m = self._model()
        r = m.compute_detection_probability(
            range_to_target=20.0, reflectivity=0.5,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0)
        assert r.model_type == DetectionModelType.EMPIRICAL
        assert r.priority == MODEL_PRIORITY[DetectionModelType.EMPIRICAL]
        assert r.has_empirical_calibration is True
        assert r.model_source == "field_trial"

    def test_reflectivity_scales_down(self):
        m = self._model()
        base = m.compute_detection_probability(
            range_to_target=20.0, reflectivity=0.5,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0).probability
        scaled = m.compute_detection_probability(
            range_to_target=20.0, reflectivity=0.25,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0).probability
        assert scaled == pytest.approx(0.25, abs=1e-9)
        assert scaled == pytest.approx(base * 0.5, abs=1e-9)
# empirical validation

class TestEmpiricalValidation:
    def test_raises_valueerror_when_one_point(self):
        with pytest.raises(ValueError, match=">= 2 calibration points"):
            EmpiricalModel(points=[(10.0, 0.8)], reflectivity=0.5, source="trial")

    def test_raises_valueerror_when_empty(self):
        with pytest.raises(ValueError):
            EmpiricalModel(points=[], reflectivity=0.5, source="trial")


class TestManufacturerCurveModel:

    def _model(self):
        return ManufacturerCurveModel(
            curve=lambda r, lo, hi: max(0.0, 1.0 - r / 100.0),
            reference_reflectivity=0.5,
            source="mfr_datasheet",
        )
# manufacturer curve behavior
    def test_maps_range_through_curve(self):
        m = self._model()
        r = m.compute_detection_probability(
            range_to_target=10.0, reflectivity=0.5,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0)
        assert r.probability == pytest.approx(0.9, abs=1e-9)
        assert r.model_type == DetectionModelType.MANUFACTURER_CURVE
        assert r.priority == MODEL_PRIORITY[DetectionModelType.MANUFACTURER_CURVE]
        assert r.has_empirical_calibration is False

    def test_scales_down_below_reference(self):
        m = self._model()
        r = m.compute_detection_probability(
            range_to_target=10.0, reflectivity=0.25,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0)
        assert r.probability == pytest.approx(0.45, abs=1e-9)



    def test_no_scale_at_or_above_reference(self):
        m = self._model()
        r = m.compute_detection_probability(
            range_to_target=10.0, reflectivity=0.7,
            incidence_angle=0.0, beam_target_overlap=1.0,
            return_strength=1.0)
        assert r.probability == pytest.approx(0.9, abs=1e-9)

    def test_can_use_always_true(self):
        assert self._model().can_use(SensorParamsView())
# resolver priority chain

class TestResolverPriorityChain:


    def _datasheet_usable(self):
        return SensorParamsView(
            max_range = 100.0,
            max_range_status = "known",
        )


    def test_empirical_wins_over_datasheet(self):
        emp = EmpiricalModel(points=EMP_2PT, reflectivity=0.5, source="trial")
        ds = DatasheetEnvelopeModel(max_range=100.0)
        resolved = resolve_detection_model(
            self._datasheet_usable() , user_empirical=emp, datasheet_envelope=ds)
        assert isinstance(resolved, EmpiricalModel)

    def test_manufacturer_wins_when_present(self):
        mfr = ManufacturerCurveModel(
            curve=lambda r, lo, hi: 0.8, reference_reflectivity=0.5, source="mfr")
        emp = EmpiricalModel(points=EMP_2PT, reflectivity=0.5, source="trial")
        ds = DatasheetEnvelopeModel(max_range=80.0)
        resolved = resolve_detection_model(
            self._datasheet_usable() , user_empirical=emp, datasheet_envelope=ds, manufacturer_curve=mfr)
        assert isinstance(resolved, ManufacturerCurveModel)
# datasheet alone + no-candidate fallback

    def test_datasheet_alone(self):
        ds = DatasheetEnvelopeModel(max_range=100.0)
        resolved = resolve_detection_model(
            self._datasheet_usable(), datasheet_envelope=ds)
        assert isinstance(resolved, DatasheetEnvelopeModel)

    def test_no_candidates_resolves_to_assumption(self):
        resolved = DetectionModelResolver().resolve(SensorParamsView())
        assert isinstance(resolved, AssumptionModel)
        result = resolved.compute_detection_probability(
            range_to_target=50.0, reflectivity=0.5, incidence_angle=0.0,
            beam_target_overlap=1.0, return_strength=1.0)
        assert result.probability is None
# rule 8: analytical / beam divergence

class TestRule8AnalyticalBeamDivergence:

    def test_can_use_false_when_beam_divergence_unknown(self):
        m = AnalyticalModel()
        params = SensorParamsView(beam_divergence=None, beam_divergence_status="unknown")
        assert m.can_use(params) is False

    def test_can_use_true_when_beam_divergence_known(self):
        m = AnalyticalModel()
        params = SensorParamsView(beam_divergence=0.003, beam_divergence_status="known")
        assert m.can_use(params) is True

    def test_resolver_falls_back_to_insufficient(self):
        resolved = DetectionModelResolver(analytical=AnalyticalModel()).resolve(
            SensorParamsView(beam_divergence=None, beam_divergence_status="unknown"))
        assert isinstance(resolved, AssumptionModel)
        result = resolved.compute_detection_probability(
            range_to_target=50.0, reflectivity=0.5, incidence_angle=0.0,
            beam_target_overlap=1.0, return_strength=1.0)
        assert result.probability is None
        assert result.model_type == DetectionModelType.ASSUMPTION

    def test_resolver_selects_analytical_when_known(self):
        resolved = DetectionModelResolver(analytical=AnalyticalModel()).resolve(
            SensorParamsView(beam_divergence=0.003, beam_divergence_status="known"))
        assert isinstance(resolved, AnalyticalModel)
# rule 8: datasheet / max_range

class TestDatasheetRule8:

    def test_can_use_false_when_max_range_unknown(self):
        m = DatasheetEnvelopeModel(max_range=100.0)
        params = SensorParamsView(max_range=None, max_range_status="unknown")
        assert m.can_use(params) is False

    def test_can_use_true_when_max_range_known(self):
        m = DatasheetEnvelopeModel(max_range=100.0)
        params = SensorParamsView(max_range=100.0, max_range_status="known")
        assert m.can_use(params) is True


# priority is recorded on each result

class TestPriorityRecording:

    def _compute(self, m):
        return m.compute_detection_probability(
            range_to_target=50.0, reflectivity=0.5, incidence_angle=0.0,
            beam_target_overlap=1.0, return_strength=1.0)
# priority values per model

    def test_empirical_priority(self):
        m = EmpiricalModel(points=EMP_2PT, reflectivity=0.5, source="t")
        r = self._compute(m)
        assert r.priority == MODEL_PRIORITY[DetectionModelType.EMPIRICAL]
        assert r.model_type == DetectionModelType.EMPIRICAL

    def test_datasheet_priority(self):
        m = DatasheetEnvelopeModel(max_range=100.0)
        r = self._compute(m)
        assert r.priority == MODEL_PRIORITY[DetectionModelType.DATASHEET]
        assert r.model_type == DetectionModelType.DATASHEET

    def test_analytical_priority(self):
        r = self._compute(AnalyticalModel())
        assert r.priority == MODEL_PRIORITY[DetectionModelType.ANALYTICAL]
        assert r.model_type == DetectionModelType.ANALYTICAL

    def test_assumption_priority(self):
        r = self._compute(AssumptionModel())
        assert r.priority == MODEL_PRIORITY[DetectionModelType.ASSUMPTION]
        assert r.model_type == DetectionModelType.ASSUMPTION
# priority: manufacturer curve

    def test_manufacturer_curve_priority(self):
        m = ManufacturerCurveModel(curve=lambda r, lo, hi: 0.7, reference_reflectivity=0.5)
        r = self._compute(m)
        assert r.priority == MODEL_PRIORITY[DetectionModelType.MANUFACTURER_CURVE]
        assert r.model_type == DetectionModelType.MANUFACTURER_CURVE


# insufficient data never fabricates a probability

class TestInsufficientData:

    def test_probability_is_none(self):
        r = insufficient_data_result()
        assert r.probability is None
        assert r.model_type == DetectionModelType.ASSUMPTION
        assert r.priority == MODEL_PRIORITY[DetectionModelType.ASSUMPTION]

    def test_notes_mentions_not_reliably_estimable(self):
        r = insufficient_data_result()
        assert "not reliably estimable" in r.notes.lower()
# backward-compatible alias

class TestModuleAlias:

    def test_alias_is_datasheet_envelope_model(self):
        assert DatasheetModel is DatasheetEnvelopeModel
        assert isinstance(DatasheetModel(max_range=50.0), DatasheetEnvelopeModel)



    def test_alias_produces_datasheet_priority(self):
        r = DatasheetModel(max_range=50.0).compute_detection_probability(
            range_to_target=30.0, reflectivity=0.5, incidence_angle=0.0,
            beam_target_overlap=1.0, return_strength=1.0)
        assert r.model_type == DetectionModelType.DATASHEET
        assert r.priority == MODEL_PRIORITY[DetectionModelType.DATASHEET]
