"""
ImmunoFit REST API

A lightweight Flask application exposing the ImmunoFit platform capabilities
via JSON endpoints.

Endpoints:
  POST /api/v1/assess           — Full immune readiness assessment
  POST /api/v1/exercise         — Exercise intervention recommendations
  POST /api/v1/predict          — Immunotherapy response prediction
  POST /api/v1/gene-expression  — Gene expression analysis
  GET  /api/v1/health           — Health check
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)

from .exercise import ExerciseInterventionRecommender
from .gene_expression import GeneExpressionAnalyzer
from .immune_readiness import ImmuneReadinessCalculator
from .models import (
    ExerciseData,
    ExerciseType,
    GeneExpressionData,
    ImmuneMarkers,
    Patient,
    Sex,
)
from .predictor import ImmunotherapyResponsePredictor

app = Flask(__name__)

_calculator   = ImmuneReadinessCalculator()
_recommender  = ExerciseInterventionRecommender()
_analyzer     = GeneExpressionAnalyzer()
_predictor    = ImmunotherapyResponsePredictor()


# ---------------------------------------------------------------------------
# Helper: build Patient from JSON request body
# ---------------------------------------------------------------------------

def _patient_from_json(data: Dict[str, Any]) -> Patient:
    """Parse and validate JSON body into a :class:`Patient` object."""
    m_data = data["immune_markers"]
    immune_markers = ImmuneMarkers(
        cd8_t_cell_count=float(m_data["cd8_t_cell_count"]),
        nk_cell_activity=float(m_data["nk_cell_activity"]),
        pd_l1_expression=float(m_data["pd_l1_expression"]),
        tumor_mutation_burden=float(m_data["tumor_mutation_burden"]),
        il6=float(m_data["il6"]),
        crp=float(m_data["crp"]),
        tnf_alpha=float(m_data["tnf_alpha"]),
        ifn_gamma=float(m_data["ifn_gamma"]),
    )

    e_data = data["exercise_data"]
    exercise_data = ExerciseData(
        vo2_max=float(e_data["vo2_max"]),
        weekly_minutes_moderate=float(e_data["weekly_minutes_moderate"]),
        weekly_minutes_vigorous=float(e_data["weekly_minutes_vigorous"]),
        steps_per_day=float(e_data["steps_per_day"]),
        exercise_type=ExerciseType(e_data.get("exercise_type", "aerobic")),
    )

    gene_expression = None
    if "gene_expression" in data and data["gene_expression"]:
        ge_data = data["gene_expression"]
        gene_expression = GeneExpressionData(
            gene_expression_profile=ge_data.get("gene_expression_profile", {}),
        )

    return Patient(
        patient_id=str(data["patient_id"]),
        age=int(data["age"]),
        sex=Sex(data["sex"]),
        cancer_type=str(data["cancer_type"]),
        immune_markers=immune_markers,
        exercise_data=exercise_data,
        gene_expression=gene_expression,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/v1/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "ImmunoFit API", "version": "0.1.0"})


@app.post("/api/v1/assess")
def assess():
    """
    Full immune readiness assessment.

    Request body: patient JSON (see _patient_from_json)
    Response: ImmuneReadinessScore as JSON
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        patient = _patient_from_json(data)
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Invalid patient data: %s", exc)
        return jsonify({"error": "Invalid patient data: missing or invalid field"}), 422

    score = _calculator.calculate(patient)
    return jsonify({
        "patient_id": patient.patient_id,
        "total_score": score.total_score,
        "level": score.level.value,
        "component_scores": score.component_scores,
        "interpretation": score.interpretation,
    })


@app.post("/api/v1/exercise")
def exercise():
    """
    Generate personalised exercise intervention recommendations.

    Request body: patient JSON (see _patient_from_json)
    Response: list of ExerciseIntervention as JSON
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        patient = _patient_from_json(data)
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Invalid patient data: %s", exc)
        return jsonify({"error": "Invalid patient data: missing or invalid field"}), 422

    score = _calculator.calculate(patient)
    interventions = _recommender.recommend(patient, score)

    return jsonify({
        "patient_id": patient.patient_id,
        "current_readiness_score": score.total_score,
        "readiness_level": score.level.value,
        "interventions": [
            {
                "exercise_type": i.exercise_type.value,
                "duration_weeks": i.duration_weeks,
                "sessions_per_week": i.sessions_per_week,
                "minutes_per_session": i.minutes_per_session,
                "target_intensity": i.target_intensity,
                "rationale": i.rationale,
                "expected_immune_improvement": i.expected_immune_improvement,
                "projected_score": _recommender.project_post_intervention_score(score, i),
            }
            for i in interventions
        ],
    })


@app.post("/api/v1/predict")
def predict():
    """
    Predict immunotherapy (anti-PD-1) response probability.

    Request body: patient JSON (see _patient_from_json)
    Response: ClinicalResponse as JSON
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        patient = _patient_from_json(data)
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Invalid patient data: %s", exc)
        return jsonify({"error": "Invalid patient data: missing or invalid field"}), 422

    score = _calculator.calculate(patient)
    response = _predictor.predict(patient, score)

    return jsonify({
        "patient_id": patient.patient_id,
        "response_probability": response.response_probability,
        "response_category": response.response_category.value,
        "confidence": response.confidence,
        "key_factors": response.key_factors,
        "recommendation": response.recommendation,
    })


@app.post("/api/v1/gene-expression")
def gene_expression_endpoint():
    """
    Analyse gene expression profile and return TME phenotype + signature scores.

    Request body: patient JSON including ``gene_expression`` field
    Response: gene expression analysis result as JSON
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        patient = _patient_from_json(data)
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Invalid patient data: %s", exc)
        return jsonify({"error": "Invalid patient data: missing or invalid field"}), 422

    result = _analyzer.analyze(patient)
    # Serialize enum value
    if result.get("tme_phenotype") is not None:
        result["tme_phenotype"] = result["tme_phenotype"].value

    return jsonify({"patient_id": patient.patient_id, **result})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    """Application factory (useful for testing and WSGI deployment)."""
    return app


if __name__ == "__main__":
    debug = os.environ.get("IMMUNOFIT_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=5000)
