"""Tests for the scholarships-by-program API endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_scholarships_by_program_returns_standard_paginated_shape(service_token_header):
    response = client.get(
        "/api/v1/scholarships/by-program/prog-001?page=1&limit=10",
        headers=service_token_header,
    )

    assert response.status_code in (200, 503)

    if response.status_code == 200:
        payload = response.json()
        assert payload["success"] is True
        assert "data" in payload
        assert "total" in payload
        assert payload["page"] == 1
        assert payload["page_size"] == 10
