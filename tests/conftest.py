"""
Shared test fixtures for the ImmunoFit test suite.
"""

import pytest

from immunofit.models import (
    ExerciseData,
    ExerciseType,
    GeneExpressionData,
    ImmuneMarkers,
    Patient,
    Sex,
)


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def make_markers(
    cd8=500.0,
    nk=45.0,
    pd_l1=55.0,
    tmb=12.0,
    il6=3.0,
    crp=2.0,
    tnf=5.0,
    ifng=30.0,
) -> ImmuneMarkers:
    return ImmuneMarkers(
        cd8_t_cell_count=cd8,
        nk_cell_activity=nk,
        pd_l1_expression=pd_l1,
        tumor_mutation_burden=tmb,
        il6=il6,
        crp=crp,
        tnf_alpha=tnf,
        ifn_gamma=ifng,
    )


def make_exercise(
    vo2=38.0,
    mod=150.0,
    vig=0.0,
    steps=8000.0,
    etype=ExerciseType.AEROBIC,
) -> ExerciseData:
    return ExerciseData(
        vo2_max=vo2,
        weekly_minutes_moderate=mod,
        weekly_minutes_vigorous=vig,
        steps_per_day=steps,
        exercise_type=etype,
    )


def make_patient(
    pid="P001",
    age=55,
    sex=Sex.MALE,
    cancer="NSCLC",
    markers: ImmuneMarkers = None,
    exercise: ExerciseData = None,
    gene_expression: GeneExpressionData = None,
) -> Patient:
    return Patient(
        patient_id=pid,
        age=age,
        sex=sex,
        cancer_type=cancer,
        immune_markers=markers or make_markers(),
        exercise_data=exercise or make_exercise(),
        gene_expression=gene_expression,
    )


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_markers():
    return make_markers()


@pytest.fixture
def default_exercise():
    return make_exercise()


@pytest.fixture
def default_patient():
    return make_patient()


@pytest.fixture
def high_readiness_patient():
    """Patient with all biomarkers indicating high immune readiness."""
    return make_patient(
        pid="HIGH001",
        markers=make_markers(cd8=800, nk=70, pd_l1=80, tmb=25, il6=1, crp=1, tnf=2, ifng=70),
        exercise=make_exercise(vo2=50, mod=200, vig=60, steps=12000),
    )


@pytest.fixture
def low_readiness_patient():
    """Patient with biomarkers indicating low immune readiness."""
    return make_patient(
        pid="LOW001",
        markers=make_markers(cd8=100, nk=10, pd_l1=0.5, tmb=2, il6=15, crp=15, tnf=20, ifng=2),
        exercise=make_exercise(vo2=18, mod=30, vig=0, steps=2000),
    )


@pytest.fixture
def gene_expression_patient():
    """Patient with gene expression data."""
    profile = {
        "CD8A": 4.5, "CD8B": 3.8, "IFNG": 5.0,
        "GZMB": 4.0, "PRF1": 3.5, "CXCL10": 4.2,
        "PDCD1": 2.5, "CD274": 3.0,
        "FOXP3": 1.5, "IL6": 2.0, "VEGFA": 1.8,
        "EOMES": 3.2, "CD27": 3.0,
    }
    ge = GeneExpressionData(gene_expression_profile=profile)
    return make_patient(pid="GE001", gene_expression=ge)
