"""Pytest configuration and shared fixtures."""

import os

import pytest

os.environ.setdefault("ALLOW_DB_FAILURE", "true")
os.environ.setdefault("USE_MOCK_DATA", "true")
os.environ.setdefault("X_SERVICE_TOKEN", "test-service-token")

from app.config import settings  # noqa: E402  # pylint: disable=wrong-import-position


@pytest.fixture
def mock_settings():
    return {
        "DB_HOST": "localhost",
        "DB_NAME": "test_db",
        "USE_MOCK_DATA": True,
        "ALLOW_DB_FAILURE": True,
        "X_SERVICE_TOKEN": settings.X_SERVICE_TOKEN,
    }


@pytest.fixture
def service_token_header():
    """Header value always matches ``settings.X_SERVICE_TOKEN`` (local + CI)."""
    return {"X-Service-Token": settings.X_SERVICE_TOKEN}


@pytest.fixture
def sample_scholarship():
    """A sample scholarship dict for testing."""
    return {
        "id": "test-scholarship-001",
        "name": "Asia-Pacific CS Master's Scholarship",
        "provider": "MIT",
        "funding_amount": 50000.00,
        "currency": "USD",
        "deadline": "2026-12-15",
        "description": "Full scholarship for CS master's students from Asia-Pacific region.",
        "eligibility_criteria": {
            "min_gpa": 3.5,
            "region": ["Asia"],
            "field_of_study": ["Computer Science"],
            "degree_level": ["master"],
        },
        "application_requirements": {
            "documents": ["CV", "Statement of Purpose", "Transcripts"],
            "recommendation_letters": 2,
        },
        "source_url": "https://www.mit.edu/scholarships/asia-pacific-cs",
        "crawled_at": "2026-03-15T10:00:00",
        "is_active": True,
    }


@pytest.fixture
def sample_student_profile():
    """A sample student profile for eligibility filtering."""
    return {
        "gpa": 3.8,
        "nationality": "India",
        "field_of_study": "Computer Science",
        "degree_type": "master",
        "language_test": "IELTS 7.5",
    }


@pytest.fixture
def sample_program_metadata():
    """A sample program metadata dict for linking."""
    return {
        "program_id": "prog-001",
        "university_name": "MIT",
        "field": "Computer Science",
        "degree_type": "master",
        "country": "United States",
    }
