"""Tests for custom exception hierarchy (including scholarship-specific errors)."""

from app.utils.exceptions import (
    CrawlError,
    DatabaseError,
    EligibilityFilterError,
    LinkingError,
    LLMExtractionError,
    NotFoundError,
    ScholarshipDiscoveryBaseError,
    ServiceAuthError,
    ValidationError,
)


def test_base_error():
    exc = ScholarshipDiscoveryBaseError("test error", 500)
    assert str(exc) == "test error"
    assert exc.status_code == 500
    assert exc.message == "test error"


def test_not_found_error():
    exc = NotFoundError("Scholarship")
    assert exc.status_code == 404
    assert "Scholarship not found" in exc.message


def test_validation_error():
    exc = ValidationError("Invalid field")
    assert exc.status_code == 422


def test_crawl_error():
    exc = CrawlError("Connection timeout")
    assert exc.status_code == 502


def test_llm_extraction_error():
    exc = LLMExtractionError("OpenAI rate limit")
    assert exc.status_code == 502


def test_linking_error():
    exc = LinkingError()
    assert exc.status_code == 500


def test_eligibility_filter_error():
    exc = EligibilityFilterError()
    assert exc.status_code == 500


def test_service_auth_error():
    exc = ServiceAuthError()
    assert exc.status_code == 401


def test_database_error():
    exc = DatabaseError()
    assert exc.status_code == 500
