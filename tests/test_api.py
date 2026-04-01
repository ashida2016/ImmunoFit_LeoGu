"""Tests for the Flask REST API (immunofit/api.py)."""

import json
import pytest

from immunofit.api import create_app


@pytest.fixture
def client():
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Shared test payload
# ---------------------------------------------------------------------------

VALID_PAYLOAD = {
    "patient_id": "TEST001",
    "age": 58,
    "sex": "male",
    "cancer_type": "NSCLC",
    "immune_markers": {
        "cd8_t_cell_count": 500,
        "nk_cell_activity": 45,
        "pd_l1_expression": 55,
        "tumor_mutation_burden": 12,
        "il6": 3,
        "crp": 2,
        "tnf_alpha": 5,
        "ifn_gamma": 30,
    },
    "exercise_data": {
        "vo2_max": 38,
        "weekly_minutes_moderate": 150,
        "weekly_minutes_vigorous": 30,
        "steps_per_day": 8000,
        "exercise_type": "aerobic",
    },
}

PAYLOAD_WITH_GENE_EXPRESSION = {
    **VALID_PAYLOAD,
    "gene_expression": {
        "gene_expression_profile": {
            "CD8A": 4.5,
            "CD8B": 3.8,
            "IFNG": 5.0,
            "GZMB": 4.0,
            "PRF1": 3.5,
            "CXCL10": 4.2,
            "PDCD1": 2.5,
            "CD274": 3.0,
            "FOXP3": 1.5,
            "IL6": 2.0,
            "VEGFA": 1.8,
        }
    },
}


class TestHealthEndpoint:
    def test_health_ok(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "ok"
        assert "ImmunoFit" in data["service"]


class TestAssessEndpoint:
    def test_assess_returns_200(self, client):
        r = client.post("/api/v1/assess", json=VALID_PAYLOAD)
        assert r.status_code == 200

    def test_assess_returns_score(self, client):
        r = client.post("/api/v1/assess", json=VALID_PAYLOAD)
        data = r.get_json()
        assert "total_score" in data
        assert 0 <= data["total_score"] <= 100

    def test_assess_returns_level(self, client):
        r = client.post("/api/v1/assess", json=VALID_PAYLOAD)
        data = r.get_json()
        assert data["level"] in ("low", "moderate", "high")

    def test_assess_returns_component_scores(self, client):
        r = client.post("/api/v1/assess", json=VALID_PAYLOAD)
        data = r.get_json()
        assert "component_scores" in data
        assert len(data["component_scores"]) > 0

    def test_assess_missing_immune_markers_returns_422(self, client):
        bad_payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "immune_markers"}
        r = client.post("/api/v1/assess", json=bad_payload)
        assert r.status_code == 422

    def test_assess_no_body_returns_400(self, client):
        r = client.post("/api/v1/assess", data="not json",
                        content_type="application/json")
        # Empty or invalid JSON → 400 or 422
        assert r.status_code in (400, 422)

    def test_assess_contains_patient_id(self, client):
        r = client.post("/api/v1/assess", json=VALID_PAYLOAD)
        data = r.get_json()
        assert data["patient_id"] == VALID_PAYLOAD["patient_id"]


class TestExerciseEndpoint:
    def test_exercise_returns_200(self, client):
        r = client.post("/api/v1/exercise", json=VALID_PAYLOAD)
        assert r.status_code == 200

    def test_exercise_returns_interventions_list(self, client):
        r = client.post("/api/v1/exercise", json=VALID_PAYLOAD)
        data = r.get_json()
        assert "interventions" in data
        assert isinstance(data["interventions"], list)
        assert len(data["interventions"]) > 0

    def test_exercise_intervention_fields(self, client):
        r = client.post("/api/v1/exercise", json=VALID_PAYLOAD)
        data = r.get_json()
        i = data["interventions"][0]
        required_fields = {
            "exercise_type", "duration_weeks", "sessions_per_week",
            "minutes_per_session", "target_intensity", "rationale",
            "expected_immune_improvement", "projected_score",
        }
        assert required_fields.issubset(set(i.keys()))

    def test_exercise_projected_score_bounded(self, client):
        r = client.post("/api/v1/exercise", json=VALID_PAYLOAD)
        data = r.get_json()
        for i in data["interventions"]:
            assert 0 <= i["projected_score"] <= 100


class TestPredictEndpoint:
    def test_predict_returns_200(self, client):
        r = client.post("/api/v1/predict", json=VALID_PAYLOAD)
        assert r.status_code == 200

    def test_predict_returns_probability(self, client):
        r = client.post("/api/v1/predict", json=VALID_PAYLOAD)
        data = r.get_json()
        assert "response_probability" in data
        assert 0 <= data["response_probability"] <= 1

    def test_predict_returns_category(self, client):
        r = client.post("/api/v1/predict", json=VALID_PAYLOAD)
        data = r.get_json()
        assert data["response_category"] in (
            "non_responder", "partial_responder", "responder"
        )

    def test_predict_returns_key_factors(self, client):
        r = client.post("/api/v1/predict", json=VALID_PAYLOAD)
        data = r.get_json()
        assert "key_factors" in data
        assert len(data["key_factors"]) > 0

    def test_predict_missing_exercise_data_returns_422(self, client):
        bad_payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "exercise_data"}
        r = client.post("/api/v1/predict", json=bad_payload)
        assert r.status_code == 422


class TestGeneExpressionEndpoint:
    def test_gene_expression_returns_200(self, client):
        r = client.post("/api/v1/gene-expression", json=PAYLOAD_WITH_GENE_EXPRESSION)
        assert r.status_code == 200

    def test_gene_expression_returns_tme_phenotype(self, client):
        r = client.post("/api/v1/gene-expression", json=PAYLOAD_WITH_GENE_EXPRESSION)
        data = r.get_json()
        assert "tme_phenotype" in data
        assert data["tme_phenotype"] in ("inflamed", "excluded", "desert")

    def test_gene_expression_no_data_returns_null_phenotype(self, client):
        r = client.post("/api/v1/gene-expression", json=VALID_PAYLOAD)
        data = r.get_json()
        assert data["tme_phenotype"] is None

    def test_gene_expression_returns_scores(self, client):
        r = client.post("/api/v1/gene-expression", json=PAYLOAD_WITH_GENE_EXPRESSION)
        data = r.get_json()
        for key in ("t_effector_score", "ifn_gamma_score", "suppression_score"):
            assert key in data
            assert data[key] is not None
