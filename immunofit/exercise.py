"""
运动干预推荐模块 (Exercise Intervention Recommendation Module)

Generates personalised exercise prescriptions designed to improve a patient's
Immune Readiness by exploiting the exercise–immune axis.

Scientific basis:
- Aerobic exercise mobilises CD8+ T cells from peripheral blood into tissues
  (Pedersen et al., Cell 2016; Campbell & Turner, Nat Rev Immunol 2019).
- Moderate-intensity exercise reduces pro-inflammatory cytokines (IL-6, TNF-α).
- HIIT acutely increases NK cell cytotoxicity and IFN-γ production.
- Resistance training sustains the muscle–immune axis via myokine secretion.
"""

from __future__ import annotations

from typing import List, Tuple

from .models import (
    ExerciseData,
    ExerciseIntervention,
    ExerciseType,
    ImmuneMarkers,
    ImmuneReadinessScore,
    Patient,
    ReadinessLevel,
)


# ---------------------------------------------------------------------------
# Prescription templates
# ---------------------------------------------------------------------------

# Each template: (ExerciseType, duration_weeks, sessions_per_week,
#                 minutes_per_session, target_intensity, rationale,
#                 expected_immune_improvement)

_AEROBIC_MODERATE: Tuple = (
    ExerciseType.AEROBIC,
    12,
    5,
    40,
    "50–70 % VO₂max (中等强度有氧)",
    (
        "中等强度有氧运动通过肾上腺素介导的机制，促使效应CD8+ T细胞和NK细胞从淋巴结和外周血"
        "向肿瘤微环境迁移，同时降低IL-6和TNF-α等促炎细胞因子水平，改善免疫抑制性微环境。"
    ),
    12.0,
)

_AEROBIC_VIGOROUS: Tuple = (
    ExerciseType.AEROBIC,
    8,
    4,
    45,
    "70–80 % VO₂max (较高强度有氧)",
    (
        "高强度有氧训练可显著提升VO₂max，增强线粒体功能，并通过IFN-γ的产生激活抗肿瘤免疫应答，"
        "适合基础体能较好的患者。"
    ),
    15.0,
)

_RESISTANCE_TRAINING: Tuple = (
    ExerciseType.RESISTANCE,
    12,
    3,
    50,
    "60–75 % 1RM (中等阻力训练)",
    (
        "阻力训练通过肌肉-免疫轴分泌肌肉因子（Irisin、IL-15），刺激NK细胞增殖和细胞毒性活性，"
        "同时改善体成分、减少代谢性炎症，维持抗肿瘤免疫功能。"
    ),
    8.0,
)

_HIIT_PROTOCOL: Tuple = (
    ExerciseType.HIIT,
    6,
    3,
    30,
    "85–95 % HRmax (高强度间歇训练 4×4 min)",
    (
        "HIIT能在短期内急剧增加CD8+ T细胞和NK细胞的循环数量，并通过儿茶酚胺爆发性释放增强"
        "免疫细胞向肿瘤部位的归巢。适合免疫状态需快速提升的患者，但需充分评估体能后实施。"
    ),
    18.0,
)

_COMBINED_PROTOCOL: Tuple = (
    ExerciseType.COMBINED,
    16,
    5,
    45,
    "有氧 50–70 % VO₂max + 阻力 60–70 % 1RM (综合训练)",
    (
        "结合有氧与阻力训练的综合方案可同步激活多条免疫调节通路：改善T细胞迁移、增强NK细胞"
        "活性、降低炎症因子并优化体成分，是长期维持免疫准备度的最佳策略。"
    ),
    20.0,
)


class ExerciseInterventionRecommender:
    """
    Generates personalised exercise prescriptions for a patient based on
    their current Immune Readiness Score and exercise capacity.

    Usage::

        recommender = ExerciseInterventionRecommender()
        interventions = recommender.recommend(patient, readiness_score)
    """

    def recommend(
        self,
        patient: Patient,
        readiness_score: ImmuneReadinessScore,
    ) -> List[ExerciseIntervention]:
        """
        Return a ranked list of exercise interventions (best-fit first).

        Selection criteria:
        1. Patient's current aerobic fitness (VO₂max) determines intensity tier.
        2. Readiness level determines urgency and preferred modality.
        3. Inflammatory burden may restrict high-intensity options.
        """
        e = patient.exercise_data
        m = patient.immune_markers
        level = readiness_score.level

        candidates = self._generate_candidates(e, m, level)
        return candidates

    def _generate_candidates(
        self,
        e: ExerciseData,
        m: ImmuneMarkers,
        level: ReadinessLevel,
    ) -> List[ExerciseIntervention]:
        prescriptions: List[ExerciseIntervention] = []

        high_inflammation = m.il6 > 10.0 or m.crp > 10.0

        if level == ReadinessLevel.LOW:
            # Start conservatively with moderate aerobic; add resistance
            prescriptions.append(self._build(*_AEROBIC_MODERATE))
            prescriptions.append(self._build(*_RESISTANCE_TRAINING))
            if not high_inflammation and e.vo2_max >= 25.0:
                prescriptions.append(self._build(*_HIIT_PROTOCOL))

        elif level == ReadinessLevel.MODERATE:
            # Escalate to higher-intensity aerobic; include combined protocol
            if e.vo2_max >= 35.0:
                prescriptions.append(self._build(*_AEROBIC_VIGOROUS))
            else:
                prescriptions.append(self._build(*_AEROBIC_MODERATE))
            prescriptions.append(self._build(*_COMBINED_PROTOCOL))
            if not high_inflammation and e.vo2_max >= 30.0:
                prescriptions.append(self._build(*_HIIT_PROTOCOL))

        else:  # HIGH
            # Maintain and optimise with combined / vigorous protocols
            prescriptions.append(self._build(*_COMBINED_PROTOCOL))
            prescriptions.append(self._build(*_AEROBIC_VIGOROUS))
            prescriptions.append(self._build(*_RESISTANCE_TRAINING))

        return prescriptions

    @staticmethod
    def _build(
        exercise_type: ExerciseType,
        duration_weeks: int,
        sessions_per_week: int,
        minutes_per_session: int,
        target_intensity: str,
        rationale: str,
        expected_immune_improvement: float,
    ) -> ExerciseIntervention:
        return ExerciseIntervention(
            exercise_type=exercise_type,
            duration_weeks=duration_weeks,
            sessions_per_week=sessions_per_week,
            minutes_per_session=minutes_per_session,
            target_intensity=target_intensity,
            rationale=rationale,
            expected_immune_improvement=expected_immune_improvement,
        )

    # ------------------------------------------------------------------
    # Post-intervention score projection
    # ------------------------------------------------------------------

    def project_post_intervention_score(
        self,
        current_score: ImmuneReadinessScore,
        intervention: ExerciseIntervention,
    ) -> float:
        """
        Estimate the Immune Readiness Score after completing *intervention*.

        Improvement is modelled with diminishing returns: patients with higher
        baseline scores gain proportionally less.
        """
        current = current_score.total_score
        raw_gain = intervention.expected_immune_improvement
        # Diminishing returns: remaining headroom × gain fraction
        headroom = 100.0 - current
        fraction = raw_gain / 100.0
        projected = current + headroom * fraction
        return round(min(projected, 100.0), 2)
