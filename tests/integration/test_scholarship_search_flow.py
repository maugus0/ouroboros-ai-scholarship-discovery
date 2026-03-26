"""Integration tests for the scholarship search flow."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_scholarships_authenticated(service_token_header):
    """Authenticated search should return a response (even if empty from no DB)."""
    response = client.post(
        "/api/v1/scholarships/search",
        json={"max_results": 5},
        headers=service_token_header,
    )
    assert response.status_code in (200, 503)


def test_search_scholarships_with_student_profile(service_token_header):
    """Search with student profile should be accepted."""
    response = client.post(
        "/api/v1/scholarships/search",
        json={
            "student_profile": {
                "gpa": 3.8,
                "nationality": "India",
                "field_of_study": "Computer Science",
                "degree_type": "master",
            },
            "max_results": 10,
        },
        headers=service_token_header,
    )
    assert response.status_code in (200, 503)


def test_get_scholarship_not_found(service_token_header):
    """Getting a non-existent scholarship should return 404 or 503 (no DB)."""
    response = client.get(
        "/api/v1/scholarships/non-existent-id",
        headers=service_token_header,
    )
    assert response.status_code in (404, 503)


def test_get_scholarships_by_program(service_token_header):
    """Getting scholarships by program should return a response."""
    response = client.get(
        "/api/v1/scholarships/by-program/prog-001?min_confidence=0.4",
        headers=service_token_header,
    )
    assert response.status_code in (200, 503)
