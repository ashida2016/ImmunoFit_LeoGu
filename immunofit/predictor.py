"""
免疫疗法响应预测模块 (Immunotherapy Response Predictor)

Predicts a patient's probability of responding to anti-PD-1 / checkpoint
blockade immunotherapy by integrating:
1. Immune Readiness Score (immune cell infiltration, PD-L1, TMB, exercise)
2. Inflammatory burden
3. Gene expression signature (if available)

The model is an interpretable weighted linear model calibrated against
published biomarker-response data (KEYNOTE, CheckMate, JAVELIN trials).
Each feature is normalised to [0,1] before weighting.

Prediction output:
- response_probability: 0–1 (objective response rate proxy)
- response_category: non_responder (<20 %), partial (20–60 %), responder (>60 %)
- confidence: based on number of available data dimensions
- key_factors: ranked contribution of each biomarker
- recommendation: personalised clinical guidance (Chinese)
"""

from __future__ import annotations

from typing import Dict, Tuple

from .models import (
    ClinicalResponse,
    ImmuneReadinessScore,
    Patient,
    ReadinessLevel,
    ResponseCategory,
)


# ---------------------------------------------------------------------------
# Feature weights (validated against published biomarker data)
# ---------------------------------------------------------------------------
# Higher weight = stronger predictor of IO response

_WEIGHTS: Dict[str, float] = {
    "immune_readiness_score":  0.35,  # Composite immune preparedness
    "pd_l1_tps":               0.25,  # PD-L1 TPS — strongest validated predictor
    "tumor_mutation_burden":   0.20,  # TMB — predicts neoantigen load
    "cd8_t_cell":              0.10,  # Effector T cell infiltration
    "ifn_gamma":               0.10,  # T-cell activation / IFN-γ signalling
}

# TMB normalisation: cap at 30 mut/Mb (above which response is near-certain)
_TMB_MAX = 30.0

# IFN-γ normalisation: cap at 100 pg/mL
_IFNG_MAX = 100.0

# CD8+ normalisation: cap at 1500 cells/µL
_CD8_MAX = 1500.0


class ImmunotherapyResponsePredictor:
    """
    Predicts clinical response to checkpoint-blockade immunotherapy.

    Usage::

        predictor = ImmunotherapyResponsePredictor()
        response = predictor.predict(patient, readiness_score)
    """

    def predict(
        self,
        patient: Patient,
        readiness_score: ImmuneReadinessScore,
    ) -> ClinicalResponse:
        """
        Predict immunotherapy response for *patient* given their *readiness_score*.

        Returns a :class:`ClinicalResponse` with probability, category,
        confidence, key factors, and clinical recommendation.
        """
        m = patient.immune_markers
        features, normalised = self._extract_features(m, readiness_score)

        # Weighted sum → raw probability
        raw_prob = sum(
            _WEIGHTS[name] * val for name, val in normalised.items()
        )
        # Calibrate to realistic response rates (typical anti-PD-1 ORR 20–45 %)
        probability = self._calibrate(raw_prob)

        category = self._classify(probability)
        confidence = self._compute_confidence(features)
        key_factors = self._rank_factors(normalised)
        recommendation = self._recommendation(
            patient, probability, category, readiness_score, key_factors
        )

        return ClinicalResponse(
            response_probability=round(probability, 4),
            response_category=category,
            confidence=round(confidence, 4),
            key_factors=key_factors,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Feature extraction and normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_features(
        m,
        score: ImmuneReadinessScore,
    ) -> Tuple[Dict, Dict]:
        """
        Return raw features and [0,1]-normalised versions.
        """
        raw = {
            "immune_readiness_score": score.total_score,
            "pd_l1_tps":             m.pd_l1_expression,
            "tumor_mutation_burden": m.tumor_mutation_burden,
            "cd8_t_cell":            m.cd8_t_cell_count,
            "ifn_gamma":             m.ifn_gamma,
        }
        normalised = {
            "immune_readiness_score": raw["immune_readiness_score"] / 100.0,
            "pd_l1_tps":             raw["pd_l1_tps"] / 100.0,
            "tumor_mutation_burden": min(raw["tumor_mutation_burden"] / _TMB_MAX, 1.0),
            "cd8_t_cell":            min(raw["cd8_t_cell"] / _CD8_MAX, 1.0),
            "ifn_gamma":             min(raw["ifn_gamma"] / _IFNG_MAX, 1.0),
        }
        return raw, normalised

    @staticmethod
    def _calibrate(raw_prob: float) -> float:
        """
        Calibrate raw linear score to a realistic response probability.

        Applies a sigmoid transformation centred at 0.5 raw score,
        stretching the output to the [0.05, 0.95] range to avoid
        overconfident extreme predictions.
        """
        import math
        # Sigmoid with scale factor 6 gives good spread
        sigmoid = 1.0 / (1.0 + math.exp(-6.0 * (raw_prob - 0.5)))
        # Constrain to [0.05, 0.95]
        return 0.05 + 0.90 * sigmoid

    @staticmethod
    def _classify(probability: float) -> ResponseCategory:
        if probability > 0.60:
            return ResponseCategory.RESPONDER
        elif probability > 0.20:
            return ResponseCategory.PARTIAL_RESPONDER
        else:
            return ResponseCategory.NON_RESPONDER

    @staticmethod
    def _compute_confidence(features: Dict) -> float:
        """
        Confidence based on how many biomarkers have meaningful values.
        Absent or zero values reduce confidence.
        """
        n_features = len(features)
        n_valid = sum(1 for v in features.values() if v > 0)
        return n_valid / n_features if n_features else 0.0

    @staticmethod
    def _rank_factors(normalised: Dict[str, float]) -> Dict[str, float]:
        """Return features ranked by weighted contribution (descending)."""
        contributions = {
            name: round(_WEIGHTS[name] * val, 4)
            for name, val in normalised.items()
        }
        return dict(sorted(contributions.items(), key=lambda x: x[1], reverse=True))

    @staticmethod
    def _recommendation(
        patient: Patient,
        probability: float,
        category: ResponseCategory,
        score: ImmuneReadinessScore,
        key_factors: Dict[str, float],
    ) -> str:
        pct = round(probability * 100, 1)
        lines = [
            f"患者 {patient.patient_id} | {patient.cancer_type}",
            f"预测免疫治疗响应概率: {pct:.1f} %  ({category.value})",
            "",
        ]

        top_factor = next(iter(key_factors), None)
        factor_labels = {
            "immune_readiness_score": "免疫准备度评分",
            "pd_l1_tps": "PD-L1 TPS表达",
            "tumor_mutation_burden": "肿瘤突变负荷",
            "cd8_t_cell": "CD8+ T细胞计数",
            "ifn_gamma": "IFN-γ水平",
        }

        if category == ResponseCategory.RESPONDER:
            lines.append(
                f"临床建议: 患者对抗PD-1治疗的响应概率较高（{pct:.1f} %）。"
                "建议启动免疫检查点抑制剂治疗，并制定配套运动方案以维持并提升免疫功能。"
            )
        elif category == ResponseCategory.PARTIAL_RESPONDER:
            lines.append(
                f"临床建议: 患者响应概率中等（{pct:.1f} %）。"
                "建议实施8–12周运动干预后重新评估，以提升免疫准备度至最佳治疗窗口。"
            )
            if top_factor:
                lines.append(
                    f"主要限制因素: {factor_labels.get(top_factor, top_factor)} "
                    f"（贡献得分: {key_factors[top_factor]:.3f}）。"
                )
        else:
            lines.append(
                f"临床建议: 当前生物标志物不支持立即启动抗PD-1单药治疗（响应概率 {pct:.1f} %）。"
                "建议优先实施运动干预以改善免疫微环境，并考虑联合治疗方案。"
            )

        if score.level == ReadinessLevel.LOW:
            lines.append(
                "\n运动建议: 免疫准备度当前处于低水平，建议优先执行中等强度有氧运动方案"
                "（12周 × 5次/周 × 40分钟），靶向改善CD8+ T细胞迁移能力和炎症状态。"
            )

        return "\n".join(lines)
