"""Tests for service-token middleware."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_public_health_does_not_require_service_token():
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_api_requires_service_token():
    response = client.get("/api/v1/scholarships/by-program/prog-001")
    assert response.status_code == 401
    assert response.json()["detail"] == "X-Service-Token header required"


def test_protected_api_rejects_invalid_service_token():
    response = client.get(
        "/api/v1/scholarships/by-program/prog-001",
        headers={"X-Service-Token": "wrong-token"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid service token"
