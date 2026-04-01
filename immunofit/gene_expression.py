"""
基因表达分析模块 (Gene Expression Analysis Module)

Analyses RNA-seq / microarray gene expression data to:
1. Compute immune gene signature scores (T-effector, IFN-γ, immunosuppression).
2. Assess the Tumour Microenvironment (TME) immune phenotype.
3. Identify exercise-responsive genes with immunological relevance.
4. Integrate gene expression with clinical biomarkers.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple

from .models import GeneExpressionData, ImmuneMarkers, Patient


# ---------------------------------------------------------------------------
# TME immune phenotype classification
# (Gajewski et al., Nat Cancer 2021; Cristescu et al., Science 2018)
# ---------------------------------------------------------------------------

class TMEPhenotype(str, Enum):
    """Tumour Microenvironment immune phenotype."""
    INFLAMED      = "inflamed"       # T cell-inflamed, best prognosis for IO
    EXCLUDED      = "excluded"       # T cells present but excluded from tumour core
    DESERT        = "desert"         # T cell-depleted, poorest IO prognosis


# ---------------------------------------------------------------------------
# Gene sets (curated from literature)
# ---------------------------------------------------------------------------

# T-effector / IFN-γ signature (Herbst et al., Nature 2014; Tumeh et al., 2014)
T_EFFECTOR_GENES: List[str] = ["CD8A", "EOMES", "PRF1", "IFNG", "CD27"]

# IFN-γ response signature (Ayers et al., JCI 2017 — 18-gene IO signature)
IFN_GAMMA_SIGNATURE: List[str] = [
    "CD274", "PDCD1LG2", "JAK2", "BRAF", "STK11",
    "IFNG", "CCL5", "CXCL9", "CXCL10", "HLA-DRA",
    "STAT1", "IDO1", "CD8A", "GZMK", "CCR5", "TIGIT", "CD27", "FOXP3",
]

# Immunosuppressive / exclusion signature
SUPPRESSION_GENES: List[str] = [
    "FOXP3", "IL10", "TGFB1", "VEGFA", "CD163",
    "ARG1", "IDO1", "MRC1",
]

# Exercise-responsive immune genes (Pedersen et al., Cell 2016; Zimmer et al., 2022)
EXERCISE_RESPONSIVE_GENES: List[str] = [
    "IFNG", "IL6", "IL15", "CXCL10", "CD8A",
    "PRF1", "GZMB", "KLRK1",   # NKG2D
    "TNFSF10",                   # TRAIL — apoptosis in tumour cells
]


class GeneExpressionAnalyzer:
    """
    Analyses a patient's gene expression profile to derive immunologically
    relevant signatures and TME phenotype classification.

    Usage::

        analyzer = GeneExpressionAnalyzer()
        result = analyzer.analyze(patient)
    """

    def analyze(self, patient: Patient) -> Dict:
        """
        Perform full gene expression analysis for *patient*.

        Returns a dictionary with:
        - ``tme_phenotype``: :class:`TMEPhenotype`
        - ``t_effector_score``: float
        - ``ifn_gamma_score``: float
        - ``suppression_score``: float
        - ``immune_gene_signature``: float (composite)
        - ``exercise_responsive_genes``: Dict[str, float]
        - ``interpretation``: str
        """
        if patient.gene_expression is None:
            return {
                "tme_phenotype": None,
                "t_effector_score": None,
                "ifn_gamma_score": None,
                "suppression_score": None,
                "immune_gene_signature": None,
                "exercise_responsive_genes": {},
                "interpretation": "未提供基因表达数据。",
            }

        ge = patient.gene_expression

        t_eff  = self._mean_expression(ge, T_EFFECTOR_GENES)
        ifng   = self._mean_expression(ge, IFN_GAMMA_SIGNATURE)
        supp   = self._mean_expression(ge, SUPPRESSION_GENES)
        sig    = ge.compute_immune_signature_score()
        exer_genes = self._exercise_gene_profile(ge)
        pheno  = self._classify_tme(t_eff, ifng, supp)

        interpretation = self._interpret(
            patient, pheno, t_eff, ifng, supp, sig, exer_genes
        )

        return {
            "tme_phenotype": pheno,
            "t_effector_score": round(t_eff, 4) if t_eff is not None else None,
            "ifn_gamma_score": round(ifng, 4) if ifng is not None else None,
            "suppression_score": round(supp, 4) if supp is not None else None,
            "immune_gene_signature": sig,
            "exercise_responsive_genes": exer_genes,
            "interpretation": interpretation,
        }

    # ------------------------------------------------------------------
    # Signature scoring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mean_expression(
        ge: GeneExpressionData,
        gene_list: List[str],
    ) -> Optional[float]:
        """Return mean expression of available genes in *gene_list*, or None."""
        values = [
            ge.gene_expression_profile[g]
            for g in gene_list
            if g in ge.gene_expression_profile
        ]
        if not values:
            return None
        return sum(values) / len(values)

    @staticmethod
    def _exercise_gene_profile(ge: GeneExpressionData) -> Dict[str, float]:
        """Return expression values for exercise-responsive immune genes."""
        return {
            gene: ge.gene_expression_profile[gene]
            for gene in EXERCISE_RESPONSIVE_GENES
            if gene in ge.gene_expression_profile
        }

    @staticmethod
    def _classify_tme(
        t_eff: Optional[float],
        ifng: Optional[float],
        supp: Optional[float],
    ) -> TMEPhenotype:
        """
        Classify the TME immune phenotype.

        Rules (simplified from Gajewski framework):
        - High T-eff AND high IFN-γ AND low suppression → INFLAMED
        - High suppression relative to T-eff → EXCLUDED
        - Low T-eff AND low IFN-γ → DESERT
        """
        if t_eff is None or ifng is None or supp is None:
            return TMEPhenotype.DESERT  # conservative default

        if t_eff >= 3.0 and ifng >= 3.0 and supp < t_eff:
            return TMEPhenotype.INFLAMED
        elif supp >= t_eff or (t_eff >= 2.0 and supp >= 3.0):
            return TMEPhenotype.EXCLUDED
        else:
            return TMEPhenotype.DESERT

    @staticmethod
    def _interpret(
        patient: Patient,
        pheno: TMEPhenotype,
        t_eff: Optional[float],
        ifng: Optional[float],
        supp: Optional[float],
        sig: float,
        exer_genes: Dict[str, float],
    ) -> str:
        lines = [
            f"患者 {patient.patient_id} 基因表达分析报告",
            f"肿瘤微环境 (TME) 表型: {pheno.value.upper()}",
            "",
        ]

        if t_eff is not None:
            lines.append(f"T效应细胞签名评分: {t_eff:.3f}")
        if ifng is not None:
            lines.append(f"IFN-γ反应签名评分: {ifng:.3f}")
        if supp is not None:
            lines.append(f"免疫抑制签名评分: {supp:.3f}")
        lines.append(f"综合免疫基因签名评分: {sig:.3f}")
        lines.append("")

        # TME phenotype interpretation
        pheno_map = {
            TMEPhenotype.INFLAMED: (
                "炎症型TME: 肿瘤微环境富含效应T细胞，IFN-γ信号通路激活，"
                "预测对抗PD-1治疗有较好响应。"
            ),
            TMEPhenotype.EXCLUDED: (
                "排他型TME: T细胞存在但被阻隔于肿瘤基质外，可能由TGF-β或VEGFA"
                "介导的免疫排斥机制导致。建议联合运动干预以促进T细胞向肿瘤核心迁移。"
            ),
            TMEPhenotype.DESERT: (
                "荒漠型TME: T细胞浸润极少，抗肿瘤免疫应答匮乏。"
                "运动干预可通过提升循环CD8+ T细胞数量和肿瘤归巢能力，改善免疫沙漠表型。"
            ),
        }
        lines.append(pheno_map.get(pheno, ""))

        # Exercise-responsive genes
        if exer_genes:
            lines.append("")
            lines.append("运动响应性免疫基因表达:")
            for gene, val in sorted(exer_genes.items()):
                lines.append(f"  {gene}: {val:.3f}")

        return "\n".join(lines)
