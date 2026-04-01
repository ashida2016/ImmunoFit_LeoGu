"""Tests for data models (immunofit/models.py)."""

import pytest
from datetime import date

from immunofit.models import (
    ClinicalResponse,
    ExerciseData,
    ExerciseType,
    GeneExpressionData,
    ImmuneMarkers,
    ImmuneReadinessScore,
    Patient,
    ReadinessLevel,
    ResponseCategory,
    Sex,
)
from tests.conftest import make_markers, make_exercise, make_patient


class TestImmuneMarkers:
    def test_valid_creation(self):
        m = make_markers()
        assert m.cd8_t_cell_count == 500.0
        assert m.nk_cell_activity == 45.0

    def test_nk_activity_out_of_range_raises(self):
        with pytest.raises(ValueError, match="nk_cell_activity"):
            ImmuneMarkers(
                cd8_t_cell_count=500, nk_cell_activity=110,
                pd_l1_expression=50, tumor_mutation_burden=10,
                il6=3, crp=2, tnf_alpha=5, ifn_gamma=20,
            )

    def test_pd_l1_out_of_range_raises(self):
        with pytest.raises(ValueError, match="pd_l1_expression"):
            ImmuneMarkers(
                cd8_t_cell_count=500, nk_cell_activity=50,
                pd_l1_expression=101, tumor_mutation_burden=10,
                il6=3, crp=2, tnf_alpha=5, ifn_gamma=20,
            )

    def test_negative_cd8_raises(self):
        with pytest.raises(ValueError, match="cd8_t_cell_count"):
            ImmuneMarkers(
                cd8_t_cell_count=-1, nk_cell_activity=50,
                pd_l1_expression=50, tumor_mutation_burden=10,
                il6=3, crp=2, tnf_alpha=5, ifn_gamma=20,
            )

    def test_negative_tmb_raises(self):
        with pytest.raises(ValueError, match="tumor_mutation_burden"):
            ImmuneMarkers(
                cd8_t_cell_count=500, nk_cell_activity=50,
                pd_l1_expression=50, tumor_mutation_burden=-1,
                il6=3, crp=2, tnf_alpha=5, ifn_gamma=20,
            )


class TestExerciseData:
    def test_valid_creation(self):
        e = make_exercise()
        assert e.vo2_max == 38.0
        assert e.exercise_type == ExerciseType.AEROBIC

    def test_metabolic_equivalents(self):
        e = ExerciseData(
            vo2_max=35, weekly_minutes_moderate=100,
            weekly_minutes_vigorous=50, steps_per_day=8000,
        )
        # 100 * 3.5 + 50 * 7.0 = 350 + 350 = 700
        assert e.metabolic_equivalents == pytest.approx(700.0)

    def test_negative_vo2max_raises(self):
        with pytest.raises(ValueError):
            ExerciseData(vo2_max=-5, weekly_minutes_moderate=100,
                         weekly_minutes_vigorous=0, steps_per_day=5000)

    def test_negative_minutes_raises(self):
        with pytest.raises(ValueError):
            ExerciseData(vo2_max=30, weekly_minutes_moderate=-10,
                         weekly_minutes_vigorous=0, steps_per_day=5000)


class TestGeneExpressionData:
    def test_get_expression_present(self):
        ge = GeneExpressionData(gene_expression_profile={"CD8A": 4.5, "IFNG": 3.0})
        assert ge.get_expression("CD8A") == pytest.approx(4.5)

    def test_get_expression_missing(self):
        ge = GeneExpressionData(gene_expression_profile={"CD8A": 4.5})
        assert ge.get_expression("FOXP3") is None

    def test_compute_immune_signature_score_all_genes(self):
        profile = {
            "CD8A": 3.0, "CD8B": 3.0, "IFNG": 3.0,
            "GZMB": 3.0, "PRF1": 3.0, "CXCL10": 3.0,
            "PDCD1": 3.0, "CD274": 3.0,
            "FOXP3": 3.0, "IL6": 3.0, "VEGFA": 3.0,
        }
        ge = GeneExpressionData(gene_expression_profile=profile)
        score = ge.compute_immune_signature_score()
        # All expressions equal → activating - suppressive terms
        # weights: +1.5+1.5+2.0+1.5+1.5+1.0+1.0+1.0 - 1.5 - 1.0 - 1.0 = 7.5
        # avg = 7.5 / 11 * 3.0 = 2.0454...
        assert score == pytest.approx(2.0455, rel=1e-2)

    def test_compute_score_empty_profile_returns_zero(self):
        ge = GeneExpressionData()
        assert ge.compute_immune_signature_score() == 0.0


class TestPatient:
    def test_valid_patient(self, default_patient):
        assert default_patient.patient_id == "P001"
        assert default_patient.age == 55

    def test_empty_patient_id_raises(self):
        with pytest.raises(ValueError, match="patient_id"):
            make_patient(pid="")

    def test_non_positive_age_raises(self):
        with pytest.raises(ValueError, match="age"):
            make_patient(age=0)

    def test_treatment_history_default_empty(self, default_patient):
        assert default_patient.treatment_history == []

    def test_gene_expression_optional(self, default_patient):
        assert default_patient.gene_expression is None


class TestImmuneReadinessScore:
    def test_valid_score(self):
        s = ImmuneReadinessScore(total_score=65.0, level=ReadinessLevel.MODERATE)
        assert s.total_score == 65.0

    def test_out_of_range_score_raises(self):
        with pytest.raises(ValueError, match="total_score"):
            ImmuneReadinessScore(total_score=105.0, level=ReadinessLevel.HIGH)


class TestClinicalResponse:
    def test_valid_response(self):
        r = ClinicalResponse(
            response_probability=0.75,
            response_category=ResponseCategory.RESPONDER,
            confidence=0.9,
        )
        assert r.response_probability == 0.75

    def test_invalid_probability_raises(self):
        with pytest.raises(ValueError, match="response_probability"):
            ClinicalResponse(
                response_probability=1.5,
                response_category=ResponseCategory.RESPONDER,
                confidence=0.9,
            )

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            ClinicalResponse(
                response_probability=0.5,
                response_category=ResponseCategory.PARTIAL_RESPONDER,
                confidence=-0.1,
            )
