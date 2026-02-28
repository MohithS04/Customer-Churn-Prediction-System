"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_health_endpoint():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data


@pytest.mark.skip(reason="Requires model and test data")
def test_predict_churn():
    """Test churn prediction endpoint."""
    response = client.post(
        "/predict/churn",
        json={
            "customer_id": "TEST_CUSTOMER",
            "prediction_horizon_days": 30
        }
    )
    # This will fail without model, which is expected
    pass
