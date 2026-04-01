"""
免疫准备度评分引擎 (Immune Readiness Scoring Engine)

Quantifies a patient's "Immune Readiness" — the biological capacity to mount
an effective anti-tumour immune response, with particular relevance to
checkpoint-blockade immunotherapy (e.g. anti-PD-1).

Scoring Dimensions (each 0–25 points; total 0–100):
1. CD8+ T-Cell Infiltration & Activation  (25 pts)
2. Checkpoint / PD-L1 Status              (25 pts)
3. Tumour Mutational Burden & Neoantigens (25 pts)
4. Exercise Capacity & Immune-Exercise Axis (25 pts)

Readiness Levels:
  Low      0–39
  Moderate 40–69
  High     70–100
"""

from __future__ import annotations

import math
from typing import Tuple

from .models import (
    ExerciseData,
    ImmuneMarkers,
    ImmuneReadinessScore,
    Patient,
    ReadinessLevel,
)


# ---------------------------------------------------------------------------
# Reference / normalisation constants (based on published clinical ranges)
# ---------------------------------------------------------------------------

# CD8+ T cell: 150–900 cells/µL in healthy adults
_CD8_LOWER = 150.0
_CD8_UPPER = 900.0

# IFN-γ: <5 pg/mL normal; >50 pg/mL strongly activated
_IFNG_ACTIVATION_THRESHOLD = 50.0

# NK activity: 10–80 % typical; >50 % favourable
_NK_HIGH = 50.0

# PD-L1 TPS for anti-PD-1 stratification (KEYNOTE thresholds)
_PDL1_STRONG_POSITIVE = 50.0  # strong positive ≥50 %
_PDL1_WEAK_POSITIVE   = 1.0   # weak positive ≥1 %

# TMB thresholds (mut/Mb; FDA cut-off ≥10 for tissue-agnostic approval)
_TMB_HIGH    = 10.0
_TMB_VERY_HIGH = 20.0

# VO₂max references (mL/kg/min; median values for age 40–60 by sex)
_VO2MAX_POOR   = 20.0
_VO2MAX_AVG    = 32.0
_VO2MAX_GOOD   = 42.0

# WHO/ACSM minimum physical activity (150 min moderate / 75 min vigorous)
_MET_MIN_THRESHOLD = 600.0  # 150 min × 4 MET-min equivalent


class ImmuneReadinessCalculator:
    """
    Calculates the Immune Readiness Score (免疫准备度评分) for a patient.

    Usage::

        calculator = ImmuneReadinessCalculator()
        score = calculator.calculate(patient)
    """

    # Component weights (must sum to 100)
    _WEIGHT_T_CELL   = 25.0
    _WEIGHT_CHECKPOINT = 25.0
    _WEIGHT_TMB      = 25.0
    _WEIGHT_EXERCISE = 25.0

    # Inflammation penalty cap (removes up to 10 points for high inflammation)
    _MAX_INFLAMMATION_PENALTY = 10.0

    def calculate(self, patient: Patient) -> ImmuneReadinessScore:
        """
        Compute the Immune Readiness Score for *patient*.

        Returns an :class:`ImmuneReadinessScore` instance with the total score,
        per-component breakdown, readiness level, and a clinical interpretation.
        """
        m = patient.immune_markers
        e = patient.exercise_data

        t_cell_score     = self._score_t_cell(m)
        checkpoint_score = self._score_checkpoint(m)
        tmb_score        = self._score_tmb(m)
        exercise_score   = self._score_exercise(e)
        inflammation_penalty = self._inflammation_penalty(m)

        raw = (
            t_cell_score
            + checkpoint_score
            + tmb_score
            + exercise_score
            - inflammation_penalty
        )
        total = max(0.0, min(100.0, round(raw, 2)))
        level = self._classify(total)

        component_scores = {
            "t_cell_activation":    round(t_cell_score, 2),
            "checkpoint_status":    round(checkpoint_score, 2),
            "tumor_mutation_burden": round(tmb_score, 2),
            "exercise_capacity":    round(exercise_score, 2),
            "inflammation_penalty": round(-inflammation_penalty, 2),
        }

        interpretation = self._interpret(total, level, component_scores, patient)

        return ImmuneReadinessScore(
            total_score=total,
            level=level,
            component_scores=component_scores,
            interpretation=interpretation,
        )

    # ------------------------------------------------------------------
    # Component scoring methods
    # ------------------------------------------------------------------

    def _score_t_cell(self, m: ImmuneMarkers) -> float:
        """
        Score CD8+ T-cell infiltration and activation (0–25).

        Combines:
        - CD8+ count relative to normal range        (0–15 pts)
        - IFN-γ as T-cell activation signal           (0–6 pts)
        - NK cell cytotoxicity                        (0–4 pts)
        """
        # CD8 sub-score (0–15): sigmoid centred at upper normal limit
        cd8_norm = (m.cd8_t_cell_count - _CD8_LOWER) / (_CD8_UPPER - _CD8_LOWER)
        cd8_sub = 15.0 * self._sigmoid(cd8_norm, k=3.0)

        # IFN-γ sub-score (0–6)
        ifng_norm = min(m.ifn_gamma / _IFNG_ACTIVATION_THRESHOLD, 1.0)
        ifng_sub = 6.0 * ifng_norm

        # NK sub-score (0–4)
        nk_norm = min(m.nk_cell_activity / 100.0, 1.0)
        nk_sub = 4.0 * nk_norm

        return cd8_sub + ifng_sub + nk_sub

    def _score_checkpoint(self, m: ImmuneMarkers) -> float:
        """
        Score checkpoint / PD-L1 status (0–25).

        Higher PD-L1 expression predicts better anti-PD-1 response, so it
        contributes positively.  The score is non-linear to reflect clinical
        cut-offs (TPS 1 % and 50 %).
        """
        tps = m.pd_l1_expression
        if tps >= _PDL1_STRONG_POSITIVE:
            # Strong positive (≥50 %): full 25 points
            return 25.0
        elif tps >= _PDL1_WEAK_POSITIVE:
            # Weak positive (1–49 %): proportional 10–24 pts
            return 10.0 + 15.0 * (tps - _PDL1_WEAK_POSITIVE) / (
                _PDL1_STRONG_POSITIVE - _PDL1_WEAK_POSITIVE
            )
        else:
            # PD-L1 negative (<1 %): 0–9 pts
            return 9.0 * tps / _PDL1_WEAK_POSITIVE

    def _score_tmb(self, m: ImmuneMarkers) -> float:
        """
        Score Tumour Mutational Burden (0–25).

        FDA-approved cut-off of 10 mut/Mb maps to ≈50 % of the component max.
        Very high TMB (≥20) gives full score.
        """
        tmb = m.tumor_mutation_burden
        if tmb >= _TMB_VERY_HIGH:
            return 25.0
        elif tmb >= _TMB_HIGH:
            return 12.5 + 12.5 * (tmb - _TMB_HIGH) / (_TMB_VERY_HIGH - _TMB_HIGH)
        else:
            return 12.5 * (tmb / _TMB_HIGH)

    def _score_exercise(self, e: ExerciseData) -> float:
        """
        Score exercise capacity and physical activity (0–25).

        Captures two dimensions:
        - Aerobic fitness (VO₂max)           (0–15 pts)
        - Weekly physical activity volume    (0–10 pts)
        """
        # VO₂max sub-score (0–15)
        if e.vo2_max >= _VO2MAX_GOOD:
            vo2_sub = 15.0
        elif e.vo2_max >= _VO2MAX_AVG:
            vo2_sub = 7.5 + 7.5 * (e.vo2_max - _VO2MAX_AVG) / (_VO2MAX_GOOD - _VO2MAX_AVG)
        else:
            vo2_sub = max(0.0, 7.5 * (e.vo2_max - _VO2MAX_POOR) / (_VO2MAX_AVG - _VO2MAX_POOR))

        # Activity volume sub-score (0–10)
        met_min = e.metabolic_equivalents
        activity_norm = min(met_min / (_MET_MIN_THRESHOLD * 2), 1.0)  # cap at 2× WHO minimum
        activity_sub = 10.0 * activity_norm

        return vo2_sub + activity_sub

    def _inflammation_penalty(self, m: ImmuneMarkers) -> float:
        """
        Penalty for high systemic inflammation (0–10 points deducted).

        Elevated IL-6, CRP, and TNF-α indicate an immunosuppressive environment
        that attenuates the immune response.
        """
        # Reference high thresholds (above which full penalty applies per marker)
        il6_ref   = 10.0   # pg/mL
        crp_ref   = 10.0   # mg/L
        tnfa_ref  = 15.0   # pg/mL

        il6_pen  = min(m.il6   / il6_ref,  1.0) * 4.0
        crp_pen  = min(m.crp   / crp_ref,  1.0) * 3.0
        tnfa_pen = min(m.tnf_alpha / tnfa_ref, 1.0) * 3.0

        return min(il6_pen + crp_pen + tnfa_pen, self._MAX_INFLAMMATION_PENALTY)

    # ------------------------------------------------------------------
    # Classification and interpretation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify(score: float) -> ReadinessLevel:
        if score >= 70:
            return ReadinessLevel.HIGH
        elif score >= 40:
            return ReadinessLevel.MODERATE
        else:
            return ReadinessLevel.LOW

    @staticmethod
    def _sigmoid(x: float, k: float = 1.0) -> float:
        """Logistic sigmoid function: 1 / (1 + exp(-k·x))."""
        return 1.0 / (1.0 + math.exp(-k * x))

    @staticmethod
    def _interpret(
        total: float,
        level: ReadinessLevel,
        components: dict,
        patient: Patient,
    ) -> str:
        lines = [
            f"患者 {patient.patient_id} | 癌症类型: {patient.cancer_type}",
            f"免疫准备度评分: {total:.1f} / 100  ({level.value.upper()})",
            "",
            "各维度评分:",
        ]
        for key, val in components.items():
            label = {
                "t_cell_activation":    "T细胞激活",
                "checkpoint_status":    "检查点/PD-L1状态",
                "tumor_mutation_burden": "肿瘤突变负荷 (TMB)",
                "exercise_capacity":    "运动能力",
                "inflammation_penalty": "炎症惩罚",
            }.get(key, key)
            lines.append(f"  {label}: {val:+.1f}")

        lines.append("")
        if level == ReadinessLevel.HIGH:
            lines.append("临床意义: 患者具有较高的免疫准备度，预计对抗PD-1免疫治疗有较好响应。")
        elif level == ReadinessLevel.MODERATE:
            lines.append(
                "临床意义: 患者免疫准备度中等。建议通过运动干预提升免疫功能，"
                "并在再次评估后决定最佳治疗时机。"
            )
        else:
            lines.append(
                "临床意义: 患者免疫准备度较低，单独使用抗PD-1治疗预期效果有限。"
                "强烈建议实施运动干预方案，以改善免疫微环境后再启动免疫治疗。"
            )

        return "\n".join(lines)
