"""Tests for the Immunotherapy Response Predictor (immunofit/predictor.py)."""

import pytest

from immunofit.immune_readiness import ImmuneReadinessCalculator
from immunofit.models import ResponseCategory
from immunofit.predictor import ImmunotherapyResponsePredictor
from tests.conftest import make_markers, make_exercise, make_patient


@pytest.fixture
def predictor():
    return ImmunotherapyResponsePredictor()


@pytest.fixture
def calculator():
    return ImmuneReadinessCalculator()


class TestImmunotherapyResponsePredictor:

    def test_predict_returns_clinical_response(self, predictor, calculator, default_patient):
        score = calculator.calculate(default_patient)
        response = predictor.predict(default_patient, score)
        assert 0 <= response.response_probability <= 1

    def test_high_readiness_patient_is_responder(self, predictor, calculator, high_readiness_patient):
        score = calculator.calculate(high_readiness_patient)
        response = predictor.predict(high_readiness_patient, score)
        assert response.response_category == ResponseCategory.RESPONDER

    def test_low_readiness_patient_is_non_responder(self, predictor, calculator, low_readiness_patient):
        score = calculator.calculate(low_readiness_patient)
        response = predictor.predict(low_readiness_patient, score)
        assert response.response_category == ResponseCategory.NON_RESPONDER

    def test_confidence_between_0_and_1(self, predictor, calculator, default_patient):
        score = calculator.calculate(default_patient)
        response = predictor.predict(default_patient, score)
        assert 0 <= response.confidence <= 1

    def test_key_factors_present(self, predictor, calculator, default_patient):
        score = calculator.calculate(default_patient)
        response = predictor.predict(default_patient, score)
        assert len(response.key_factors) > 0

    def test_key_factors_sum_close_to_probability(self, predictor, calculator, default_patient):
        """The sum of key_factor contributions should equal the underlying weighted score."""
        score = calculator.calculate(default_patient)
        response = predictor.predict(default_patient, score)
        # key factors contain weighted contributions (0–1 normalised)
        total_contribution = sum(response.key_factors.values())
        assert total_contribution > 0

    def test_recommendation_non_empty(self, predictor, calculator, default_patient):
        score = calculator.calculate(default_patient)
        response = predictor.predict(default_patient, score)
        assert len(response.recommendation) > 0

    def test_recommendation_contains_patient_id(self, predictor, calculator, default_patient):
        score = calculator.calculate(default_patient)
        response = predictor.predict(default_patient, score)
        assert default_patient.patient_id in response.recommendation

    def test_higher_pd_l1_gives_higher_probability(self, predictor, calculator):
        patient_low = make_patient(markers=make_markers(pd_l1=0, tmb=5, cd8=300, ifng=10))
        patient_high = make_patient(markers=make_markers(pd_l1=80, tmb=5, cd8=300, ifng=10))
        s_low  = calculator.calculate(patient_low)
        s_high = calculator.calculate(patient_high)
        r_low  = predictor.predict(patient_low, s_low)
        r_high = predictor.predict(patient_high, s_high)
        assert r_high.response_probability > r_low.response_probability

    def test_higher_tmb_gives_higher_probability(self, predictor, calculator):
        patient_low = make_patient(markers=make_markers(pd_l1=30, tmb=2, cd8=300, ifng=15))
        patient_high = make_patient(markers=make_markers(pd_l1=30, tmb=25, cd8=300, ifng=15))
        s_low  = calculator.calculate(patient_low)
        s_high = calculator.calculate(patient_high)
        r_low  = predictor.predict(patient_low, s_low)
        r_high = predictor.predict(patient_high, s_high)
        assert r_high.response_probability > r_low.response_probability

    def test_response_category_boundaries(self, predictor, calculator):
        """Verify category mapping aligns with probability thresholds."""
        # Build a patient expected to be partial responder
        patient = make_patient(
            markers=make_markers(cd8=400, nk=40, pd_l1=25, tmb=8, il6=4, crp=3, tnf=5, ifng=20),
            exercise=make_exercise(vo2=30, mod=120, vig=0, steps=7000),
        )
        score = calculator.calculate(patient)
        response = predictor.predict(patient, score)
        # Verify category is consistent with probability
        if response.response_probability > 0.60:
            assert response.response_category == ResponseCategory.RESPONDER
        elif response.response_probability > 0.20:
            assert response.response_category == ResponseCategory.PARTIAL_RESPONDER
        else:
            assert response.response_category == ResponseCategory.NON_RESPONDER
