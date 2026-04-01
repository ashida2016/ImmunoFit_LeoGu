"""Tests for the Exercise Intervention Recommender (immunofit/exercise.py)."""

import pytest

from immunofit.exercise import ExerciseInterventionRecommender
from immunofit.immune_readiness import ImmuneReadinessCalculator
from immunofit.models import ExerciseType, ReadinessLevel
from tests.conftest import make_markers, make_exercise, make_patient


@pytest.fixture
def recommender():
    return ExerciseInterventionRecommender()


@pytest.fixture
def calculator():
    return ImmuneReadinessCalculator()


class TestExerciseInterventionRecommender:

    def test_recommend_returns_list(self, recommender, calculator, default_patient):
        score = calculator.calculate(default_patient)
        interventions = recommender.recommend(default_patient, score)
        assert isinstance(interventions, list)
        assert len(interventions) > 0

    def test_low_readiness_includes_aerobic(self, recommender, calculator, low_readiness_patient):
        score = calculator.calculate(low_readiness_patient)
        interventions = recommender.recommend(low_readiness_patient, score)
        types = [i.exercise_type for i in interventions]
        assert ExerciseType.AEROBIC in types

    def test_high_readiness_includes_combined(self, recommender, calculator, high_readiness_patient):
        score = calculator.calculate(high_readiness_patient)
        interventions = recommender.recommend(high_readiness_patient, score)
        types = [i.exercise_type for i in interventions]
        assert ExerciseType.COMBINED in types

    def test_high_inflammation_excludes_hiit_for_low_fitness(self, recommender, calculator):
        patient = make_patient(
            markers=make_markers(il6=15, crp=12, tmb=2, pd_l1=0.5, cd8=100, nk=10, ifng=2),
            exercise=make_exercise(vo2=18, mod=30, vig=0, steps=2000),
        )
        score = calculator.calculate(patient)
        interventions = recommender.recommend(patient, score)
        types = [i.exercise_type for i in interventions]
        assert ExerciseType.HIIT not in types

    def test_all_interventions_have_positive_expected_improvement(
        self, recommender, calculator, default_patient
    ):
        score = calculator.calculate(default_patient)
        interventions = recommender.recommend(default_patient, score)
        for i in interventions:
            assert i.expected_immune_improvement > 0

    def test_intervention_fields_populated(self, recommender, calculator, default_patient):
        score = calculator.calculate(default_patient)
        interventions = recommender.recommend(default_patient, score)
        for i in interventions:
            assert i.duration_weeks > 0
            assert i.sessions_per_week > 0
            assert i.minutes_per_session > 0
            assert i.target_intensity
            assert i.rationale

    def test_project_post_intervention_score_higher_than_current(
        self, recommender, calculator, low_readiness_patient
    ):
        score = calculator.calculate(low_readiness_patient)
        interventions = recommender.recommend(low_readiness_patient, score)
        for i in interventions:
            projected = recommender.project_post_intervention_score(score, i)
            assert projected >= score.total_score

    def test_project_post_intervention_score_max_100(self, recommender, calculator):
        # Patient already near maximum readiness
        patient = make_patient(
            markers=make_markers(cd8=900, nk=80, pd_l1=95, tmb=30, il6=0.5, crp=0.5, tnf=1, ifng=90),
            exercise=make_exercise(vo2=60, mod=300, vig=120, steps=15000),
        )
        score = calculator.calculate(patient)
        interventions = recommender.recommend(patient, score)
        for i in interventions:
            projected = recommender.project_post_intervention_score(score, i)
            assert projected <= 100.0

    def test_diminishing_returns_projection(self, recommender, calculator):
        """High-baseline patient should gain less absolute points than low-baseline."""
        low_patient = make_patient(
            pid="LOW",
            markers=make_markers(cd8=100, nk=10, pd_l1=0.5, tmb=2, il6=15, crp=15, tnf=20, ifng=2),
            exercise=make_exercise(vo2=18, mod=30, vig=0, steps=2000),
        )
        high_patient = make_patient(
            pid="HIGH",
            markers=make_markers(cd8=800, nk=70, pd_l1=80, tmb=25, il6=1, crp=1, tnf=2, ifng=70),
            exercise=make_exercise(vo2=50, mod=200, vig=60, steps=12000),
        )
        s_low  = calculator.calculate(low_patient)
        s_high = calculator.calculate(high_patient)

        # Use a common template with same expected_immune_improvement
        interventions_low  = recommender.recommend(low_patient, s_low)
        interventions_high = recommender.recommend(high_patient, s_high)

        if interventions_low and interventions_high:
            gain_low  = recommender.project_post_intervention_score(s_low,  interventions_low[0])  - s_low.total_score
            gain_high = recommender.project_post_intervention_score(s_high, interventions_high[0]) - s_high.total_score
            # Low-baseline patient should gain at least as much as high-baseline
            # (diminishing returns means high already has less headroom)
            assert gain_low >= gain_high
