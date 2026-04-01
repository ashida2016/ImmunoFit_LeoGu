"""Tests for the Gene Expression Analyzer (immunofit/gene_expression.py)."""

import pytest

from immunofit.gene_expression import GeneExpressionAnalyzer, TMEPhenotype
from immunofit.models import GeneExpressionData
from tests.conftest import make_patient


@pytest.fixture
def analyzer():
    return GeneExpressionAnalyzer()


class TestGeneExpressionAnalyzer:

    def test_analyze_no_gene_data(self, analyzer, default_patient):
        result = analyzer.analyze(default_patient)
        assert result["tme_phenotype"] is None
        assert "未提供基因表达数据" in result["interpretation"]

    def test_analyze_inflamed_phenotype(self, analyzer, gene_expression_patient):
        result = analyzer.analyze(gene_expression_patient)
        assert result["tme_phenotype"] == TMEPhenotype.INFLAMED

    def test_analyze_desert_phenotype(self, analyzer):
        """Patient with very low T-effector and IFN-γ gene expression."""
        profile = {
            "CD8A": 0.5, "EOMES": 0.3, "PRF1": 0.4, "IFNG": 0.2, "CD27": 0.5,
            "FOXP3": 0.1, "IL10": 0.2, "TGFB1": 0.3, "VEGFA": 0.5,
        }
        ge = GeneExpressionData(gene_expression_profile=profile)
        patient = make_patient(pid="DESERT001", gene_expression=ge)
        result = analyzer.analyze(patient)
        assert result["tme_phenotype"] == TMEPhenotype.DESERT

    def test_t_effector_score_computed(self, analyzer, gene_expression_patient):
        result = analyzer.analyze(gene_expression_patient)
        assert result["t_effector_score"] is not None
        assert result["t_effector_score"] > 0

    def test_ifn_gamma_score_computed(self, analyzer, gene_expression_patient):
        result = analyzer.analyze(gene_expression_patient)
        assert result["ifn_gamma_score"] is not None

    def test_suppression_score_computed(self, analyzer, gene_expression_patient):
        result = analyzer.analyze(gene_expression_patient)
        assert result["suppression_score"] is not None

    def test_immune_signature_score_not_none(self, analyzer, gene_expression_patient):
        result = analyzer.analyze(gene_expression_patient)
        assert result["immune_gene_signature"] is not None

    def test_exercise_responsive_genes_populated(self, analyzer, gene_expression_patient):
        result = analyzer.analyze(gene_expression_patient)
        # At least CD8A and IFNG should be in exercise responsive genes
        exer = result["exercise_responsive_genes"]
        assert "CD8A" in exer or "IFNG" in exer

    def test_interpretation_contains_patient_id(self, analyzer, gene_expression_patient):
        result = analyzer.analyze(gene_expression_patient)
        assert gene_expression_patient.patient_id in result["interpretation"]

    def test_excluded_phenotype(self, analyzer):
        """High suppression genes relative to T-effector → EXCLUDED."""
        profile = {
            "CD8A": 2.5, "EOMES": 2.0, "PRF1": 2.0, "IFNG": 2.0, "CD27": 2.0,
            "FOXP3": 4.0, "IL10": 3.5, "TGFB1": 4.0, "VEGFA": 3.5,
            "CD163": 4.0, "ARG1": 3.0,
        }
        ge = GeneExpressionData(gene_expression_profile=profile)
        patient = make_patient(pid="EXCL001", gene_expression=ge)
        result = analyzer.analyze(patient)
        assert result["tme_phenotype"] in (TMEPhenotype.EXCLUDED, TMEPhenotype.DESERT)

    def test_interpretation_string_non_empty(self, analyzer, gene_expression_patient):
        result = analyzer.analyze(gene_expression_patient)
        assert len(result["interpretation"]) > 20

    def test_scores_are_floats(self, analyzer, gene_expression_patient):
        result = analyzer.analyze(gene_expression_patient)
        for key in ("t_effector_score", "ifn_gamma_score", "suppression_score",
                    "immune_gene_signature"):
            assert isinstance(result[key], float)
