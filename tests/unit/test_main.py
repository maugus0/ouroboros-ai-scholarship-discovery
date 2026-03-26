"""Tests for the main FastAPI application."""

from fastapi.testclient import TestClient

from app.config import APP_VERSION
from app.main import app

client = TestClient(app)


def test_app_title():
    assert app.title == "Scholarship Discovery Agent"


def test_app_version():
    assert app.version == APP_VERSION


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Scholarship Discovery Agent"


def test_root_returns_service_info():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Scholarship Discovery Agent"
    assert "version" in data


def test_health_returns_status():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
