"""Tests for the Immune Readiness Calculator (immunofit/immune_readiness.py)."""

import pytest

from immunofit.immune_readiness import ImmuneReadinessCalculator
from immunofit.models import ReadinessLevel
from tests.conftest import make_markers, make_exercise, make_patient


@pytest.fixture
def calculator():
    return ImmuneReadinessCalculator()


class TestImmuneReadinessCalculator:

    def test_calculate_returns_score(self, calculator, default_patient):
        score = calculator.calculate(default_patient)
        assert 0 <= score.total_score <= 100

    def test_high_readiness_patient(self, calculator, high_readiness_patient):
        score = calculator.calculate(high_readiness_patient)
        assert score.total_score >= 70
        assert score.level == ReadinessLevel.HIGH

    def test_low_readiness_patient(self, calculator, low_readiness_patient):
        score = calculator.calculate(low_readiness_patient)
        assert score.total_score < 40
        assert score.level == ReadinessLevel.LOW

    def test_moderate_patient(self, calculator):
        patient = make_patient(
            markers=make_markers(cd8=400, nk=40, pd_l1=20, tmb=8, il6=4, crp=3, tnf=5, ifng=20),
            exercise=make_exercise(vo2=30, mod=120, vig=0, steps=7000),
        )
        score = calculator.calculate(patient)
        assert score.level == ReadinessLevel.MODERATE

    def test_component_scores_present(self, calculator, default_patient):
        score = calculator.calculate(default_patient)
        expected_keys = {
            "t_cell_activation", "checkpoint_status",
            "tumor_mutation_burden", "exercise_capacity", "inflammation_penalty",
        }
        assert set(score.component_scores.keys()) == expected_keys

    def test_each_component_in_expected_range(self, calculator, default_patient):
        score = calculator.calculate(default_patient)
        components = score.component_scores
        # Positive components should be between 0 and 25
        for key in ("t_cell_activation", "checkpoint_status",
                    "tumor_mutation_burden", "exercise_capacity"):
            assert 0 <= components[key] <= 25, f"{key} out of expected range"
        # Inflammation penalty (stored as negative contribution)
        assert -10 <= components["inflammation_penalty"] <= 0

    def test_high_inflammation_lowers_score(self, calculator):
        low_inflam = make_patient(
            markers=make_markers(il6=1, crp=1, tnf=1),
        )
        high_inflam = make_patient(
            markers=make_markers(il6=20, crp=20, tnf=30),
        )
        s_low = calculator.calculate(low_inflam)
        s_high = calculator.calculate(high_inflam)
        assert s_low.total_score > s_high.total_score

    def test_pd_l1_strong_positive_gets_full_checkpoint_score(self, calculator):
        patient = make_patient(markers=make_markers(pd_l1=60))
        score = calculator.calculate(patient)
        assert score.component_scores["checkpoint_status"] == pytest.approx(25.0)

    def test_pd_l1_zero_gives_near_zero_checkpoint_score(self, calculator):
        patient = make_patient(markers=make_markers(pd_l1=0))
        score = calculator.calculate(patient)
        assert score.component_scores["checkpoint_status"] == pytest.approx(0.0)

    def test_very_high_tmb_gives_full_tmb_score(self, calculator):
        patient = make_patient(markers=make_markers(tmb=25))
        score = calculator.calculate(patient)
        assert score.component_scores["tumor_mutation_burden"] == pytest.approx(25.0)

    def test_score_bounded_at_zero_minimum(self, calculator, low_readiness_patient):
        score = calculator.calculate(low_readiness_patient)
        assert score.total_score >= 0.0

    def test_score_bounded_at_100_maximum(self, calculator, high_readiness_patient):
        score = calculator.calculate(high_readiness_patient)
        assert score.total_score <= 100.0

    def test_interpretation_non_empty(self, calculator, default_patient):
        score = calculator.calculate(default_patient)
        assert len(score.interpretation) > 0

    def test_interpretation_contains_patient_id(self, calculator, default_patient):
        score = calculator.calculate(default_patient)
        assert default_patient.patient_id in score.interpretation

    def test_classify_low(self, calculator):
        assert calculator._classify(30.0) == ReadinessLevel.LOW

    def test_classify_moderate(self, calculator):
        assert calculator._classify(55.0) == ReadinessLevel.MODERATE

    def test_classify_high(self, calculator):
        assert calculator._classify(75.0) == ReadinessLevel.HIGH

    def test_exercise_score_improves_with_vo2max(self, calculator):
        low_fit = make_patient(exercise=make_exercise(vo2=18, mod=50, vig=0, steps=3000))
        high_fit = make_patient(exercise=make_exercise(vo2=50, mod=200, vig=60, steps=12000))
        s_low = calculator.calculate(low_fit)
        s_high = calculator.calculate(high_fit)
        assert (
            s_high.component_scores["exercise_capacity"]
            > s_low.component_scores["exercise_capacity"]
        )
