"""
数据模型定义 (Data Model Definitions)

Core data structures for the ImmunoFit platform representing patients,
immunological markers, exercise data, gene expression profiles, and
clinical outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ExerciseType(str, Enum):
    """Supported exercise modalities."""
    AEROBIC = "aerobic"
    RESISTANCE = "resistance"
    HIIT = "hiit"
    COMBINED = "combined"


class ReadinessLevel(str, Enum):
    """Immune readiness classification."""
    LOW = "low"          # Score 0–39: 免疫准备度低
    MODERATE = "moderate"  # Score 40–69: 免疫准备度中等
    HIGH = "high"        # Score 70–100: 免疫准备度高


class ResponseCategory(str, Enum):
    """Predicted immunotherapy response category."""
    NON_RESPONDER = "non_responder"      # <20 % probability
    PARTIAL_RESPONDER = "partial_responder"  # 20–60 % probability
    RESPONDER = "responder"              # >60 % probability


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class ImmuneMarkers:
    """
    Laboratory immunological biomarkers for a patient.

    All numeric values represent clinical lab measurements:
    - cd8_t_cell_count: CD8+ T cells per µL blood
    - nk_cell_activity: NK cell cytotoxicity percentage (0–100)
    - pd_l1_expression: Tumor PD-L1 expression as Tumour Proportion Score (0–100 %)
    - tumor_mutation_burden: Mutations per megabase (mut/Mb)
    - il6: Interleukin-6 (pg/mL) — pro-inflammatory marker
    - crp: C-reactive protein (mg/L) — systemic inflammation
    - tnf_alpha: Tumour Necrosis Factor-α (pg/mL)
    - ifn_gamma: Interferon-γ (pg/mL) — T-cell activation proxy
    """

    cd8_t_cell_count: float        # cells/µL  (normal: 150–900)
    nk_cell_activity: float        # % (0–100)
    pd_l1_expression: float        # TPS % (0–100)
    tumor_mutation_burden: float   # mut/Mb
    il6: float                     # pg/mL
    crp: float                     # mg/L
    tnf_alpha: float               # pg/mL
    ifn_gamma: float               # pg/mL

    def __post_init__(self) -> None:
        if not 0 <= self.nk_cell_activity <= 100:
            raise ValueError("nk_cell_activity must be between 0 and 100")
        if not 0 <= self.pd_l1_expression <= 100:
            raise ValueError("pd_l1_expression must be between 0 and 100")
        if self.cd8_t_cell_count < 0:
            raise ValueError("cd8_t_cell_count must be non-negative")
        if self.tumor_mutation_burden < 0:
            raise ValueError("tumor_mutation_burden must be non-negative")


@dataclass
class ExerciseData:
    """
    Patient exercise capacity and activity data.

    - vo2_max: Maximal oxygen uptake (mL/kg/min) — gold standard aerobic fitness
    - weekly_minutes_moderate: Weekly minutes of moderate-intensity exercise
    - weekly_minutes_vigorous: Weekly minutes of vigorous-intensity exercise
    - steps_per_day: Average daily step count
    - exercise_type: Predominant exercise modality
    """

    vo2_max: float                          # mL/kg/min
    weekly_minutes_moderate: float          # min/week
    weekly_minutes_vigorous: float          # min/week
    steps_per_day: float                    # steps/day
    exercise_type: ExerciseType = ExerciseType.AEROBIC

    def __post_init__(self) -> None:
        if self.vo2_max < 0:
            raise ValueError("vo2_max must be non-negative")
        if self.weekly_minutes_moderate < 0 or self.weekly_minutes_vigorous < 0:
            raise ValueError("Exercise minutes must be non-negative")
        if self.steps_per_day < 0:
            raise ValueError("steps_per_day must be non-negative")

    @property
    def metabolic_equivalents(self) -> float:
        """Estimate weekly MET-minutes (metabolic equivalent task-minutes)."""
        # Moderate exercise ~3.5 MET; vigorous ~7.0 MET
        return self.weekly_minutes_moderate * 3.5 + self.weekly_minutes_vigorous * 7.0


@dataclass
class GeneExpressionData:
    """
    RNA-seq or microarray gene expression profile.

    gene_expression_profile: mapping of gene symbol → normalised expression value
    (e.g., log2-TPM or log2-FPKM).

    Key immunologically relevant genes tracked by the platform:
    - CD8A, CD8B  — cytotoxic T-cell markers
    - PDCD1 (PD-1), CD274 (PD-L1) — immune checkpoint
    - IFNG          — IFN-γ (T-cell activation)
    - GZMB, PRF1    — cytotoxicity effectors
    - FOXP3         — regulatory T cell marker (suppressive)
    - IL6, CXCL10   — inflammatory/chemo-attraction signals
    - VEGFA         — angiogenesis / immunosuppressive TME
    """

    gene_expression_profile: Dict[str, float] = field(default_factory=dict)
    immune_gene_signature_score: Optional[float] = None  # pre-computed composite

    # Canonical immune checkpoint / T-cell genes used for signature scoring
    IMMUNE_SIGNATURE_GENES: List[str] = field(
        default_factory=lambda: [
            "CD8A", "CD8B", "PDCD1", "CD274", "IFNG",
            "GZMB", "PRF1", "FOXP3", "IL6", "CXCL10", "VEGFA",
        ],
        repr=False,
        compare=False,
    )

    def get_expression(self, gene: str) -> Optional[float]:
        """Return expression value for a gene, or None if not profiled."""
        return self.gene_expression_profile.get(gene)

    def compute_immune_signature_score(self) -> float:
        """
        Compute a composite immune gene signature score.

        Activating genes (CD8A, CD8B, IFNG, GZMB, PRF1, CXCL10) contribute
        positively; suppressive genes (FOXP3, IL6, VEGFA) negatively;
        checkpoint genes (PDCD1, CD274) have a moderate positive weight
        reflecting predictive value for checkpoint blockade.
        """
        weights: Dict[str, float] = {
            "CD8A":   1.5,
            "CD8B":   1.5,
            "IFNG":   2.0,
            "GZMB":   1.5,
            "PRF1":   1.5,
            "CXCL10": 1.0,
            "PDCD1":  1.0,
            "CD274":  1.0,
            "FOXP3": -1.5,
            "IL6":   -1.0,
            "VEGFA": -1.0,
        }
        score = 0.0
        n = 0
        for gene, weight in weights.items():
            expr = self.get_expression(gene)
            if expr is not None:
                score += weight * expr
                n += 1
        if n == 0:
            return 0.0
        self.immune_gene_signature_score = round(score / n, 4)
        return self.immune_gene_signature_score


@dataclass
class Patient:
    """
    Central patient record aggregating all data used by ImmunoFit.
    """

    patient_id: str
    age: int
    sex: Sex
    cancer_type: str                    # e.g. "NSCLC", "melanoma"
    immune_markers: ImmuneMarkers
    exercise_data: ExerciseData
    gene_expression: Optional[GeneExpressionData] = None
    diagnosis_date: Optional[date] = None
    treatment_history: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.age <= 0:
            raise ValueError("age must be positive")
        if not self.patient_id:
            raise ValueError("patient_id must not be empty")


@dataclass
class ImmuneReadinessScore:
    """
    Quantified Immune Readiness (免疫准备度) for a patient.

    total_score: 0–100 composite score
    level: low / moderate / high classification
    component_scores: breakdown by dimension
    interpretation: human-readable clinical narrative
    """

    total_score: float
    level: ReadinessLevel
    component_scores: Dict[str, float] = field(default_factory=dict)
    interpretation: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.total_score <= 100:
            raise ValueError("total_score must be between 0 and 100")


@dataclass
class ExerciseIntervention:
    """
    Personalised exercise prescription generated by the platform.

    exercise_type: recommended modality
    duration_weeks: length of intervention
    sessions_per_week: training frequency
    minutes_per_session: session length
    target_intensity: e.g. "60–70 % VO₂max"
    rationale: clinical/biological justification
    expected_immune_improvement: predicted Δ immune readiness score
    """

    exercise_type: ExerciseType
    duration_weeks: int
    sessions_per_week: int
    minutes_per_session: int
    target_intensity: str
    rationale: str
    expected_immune_improvement: float  # Δ points on 0–100 scale


@dataclass
class ClinicalResponse:
    """
    Predicted clinical response to immunotherapy.

    response_probability: 0–1 probability of objective response
    response_category: non_responder / partial_responder / responder
    confidence: 0–1 model confidence
    key_factors: top biomarkers driving the prediction
    recommendation: actionable clinical guidance
    """

    response_probability: float
    response_category: ResponseCategory
    confidence: float
    key_factors: Dict[str, float] = field(default_factory=dict)
    recommendation: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.response_probability <= 1:
            raise ValueError("response_probability must be between 0 and 1")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
