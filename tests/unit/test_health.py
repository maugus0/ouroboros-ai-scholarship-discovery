"""Tests for health endpoints."""

from fastapi.testclient import TestClient

from app.api import health as health_api
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["message"] == "Scholarship Discovery Agent"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["database"] == "not_connected"


def test_health_endpoint_reports_connected_database(monkeypatch):
    async def fake_is_database_connected():
        return True

    monkeypatch.setattr(health_api, "is_database_connected", fake_is_database_connected)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["database"] == "connected"
