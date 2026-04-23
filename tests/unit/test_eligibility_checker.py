"""Tests for the new EligibilityChecker agent with detailed explainability."""

from datetime import date, timedelta

import pytest

from app.agents.eligibility_checker import EligibilityChecker


@pytest.fixture
def checker():
    """Create an EligibilityChecker instance."""
    return EligibilityChecker()


@pytest.fixture
def full_scholarship():
    """Scholarship with all eligibility criteria."""
    return {
        "id": "test-001",
        "name": "Full Criteria Scholarship",
        "provider": "MIT",
        "deadline": (date.today() + timedelta(days=30)).isoformat(),
        "eligibility_criteria": {
            "parsed_criteria": [
                {"criterion_type": "min_gpa", "criterion_value": "3.5", "is_mandatory": True},
                {"criterion_type": "degree_level", "criterion_value": "master,phd", "is_mandatory": True},
                {
                    "criterion_type": "field_of_study",
                    "criterion_value": "Computer Science,Engineering",
                    "is_mandatory": True,
                },
                {"criterion_type": "nationality", "criterion_value": "India,China", "is_mandatory": True},
                {"criterion_type": "language_test", "criterion_value": "IELTS 7.0", "is_mandatory": True},
            ]
        },
    }


@pytest.fixture
def eligible_student():
    """Student who meets all criteria."""
    return {
        "gpa": 3.8,
        "gpa_scale": 4.0,
        "nationality": "India",
        "field_of_study": "Computer Science",
        "degree_type": "master",
        "language_test": "IELTS 7.5",
    }


@pytest.fixture
def ineligible_student():
    """Student who fails some criteria."""
    return {
        "gpa": 3.2,
        "nationality": "Brazil",
        "field_of_study": "History",
        "degree_type": "bachelor",
        "language_test": "IELTS 6.0",
    }


class TestEligibilityChecker:
    """Test suite for EligibilityChecker."""

    def test_fully_eligible_student(self, checker, full_scholarship, eligible_student):
        """Test that eligible student passes all checks with reasons."""
        result = checker.check_eligibility(full_scholarship, eligible_student)

        assert result.is_eligible is True
        assert len(result.reasons_eligible) > 0
        assert len(result.reasons_ineligible) == 0
        assert len(result.missing_info) == 0
        assert result.confidence >= 0.9

    def test_ineligible_student(self, checker, full_scholarship, ineligible_student):
        """Test that ineligible student fails with clear reasons."""
        result = checker.check_eligibility(full_scholarship, ineligible_student)

        assert result.is_eligible is False
        assert len(result.reasons_ineligible) > 0
        assert any("GPA" in r for r in result.reasons_ineligible)
        assert any("Nationality" in r or "nationality" in r for r in result.reasons_ineligible)

    def test_missing_profile_fields(self, checker, full_scholarship):
        """Test that missing profile fields are tracked."""
        incomplete_student = {"gpa": 3.8}

        result = checker.check_eligibility(full_scholarship, incomplete_student)

        assert result.is_eligible is False
        assert len(result.missing_info) > 0
        assert any("Nationality" in m or "nationality" in m for m in result.missing_info)
        assert any("field" in m.lower() for m in result.missing_info)

    def test_gpa_normalization(self, checker):
        """Test GPA normalization for different scales."""
        scholarship = {
            "id": "test",
            "eligibility_criteria": {
                "parsed_criteria": [
                    {"criterion_type": "min_gpa", "criterion_value": "3.5", "is_mandatory": True},
                ]
            },
        }

        student_10_scale = {"gpa": 9.0, "gpa_scale": 10.0}
        result = checker.check_eligibility(scholarship, student_10_scale)

        assert result.is_eligible is True
        assert any("normalized" in r.lower() for r in result.reasons_eligible)

    def test_deadline_passed(self, checker):
        """Test that passed deadlines are flagged as ineligible."""
        scholarship = {
            "id": "test",
            "deadline": (date.today() - timedelta(days=5)).isoformat(),
            "eligibility_criteria": {},
        }

        result = checker.check_eligibility(scholarship, {})

        assert result.is_eligible is False
        assert any("passed" in r.lower() for r in result.reasons_ineligible)

    def test_deadline_soon(self, checker):
        """Test that upcoming deadlines are noted."""
        scholarship = {
            "id": "test",
            "deadline": (date.today() + timedelta(days=7)).isoformat(),
            "eligibility_criteria": {},
        }

        result = checker.check_eligibility(scholarship, {})

        assert result.is_eligible is True
        assert any("soon" in r.lower() or "days" in r.lower() for r in result.reasons_eligible)

    def test_region_matching(self, checker):
        """Test region-based eligibility."""
        scholarship = {
            "id": "test",
            "eligibility_criteria": {
                "parsed_criteria": [
                    {"criterion_type": "region", "criterion_value": "Asia", "is_mandatory": True},
                ]
            },
        }

        asian_student = {"nationality": "India"}
        result = checker.check_eligibility(scholarship, asian_student)
        assert result.is_eligible is True
        assert any("region" in r.lower() for r in result.reasons_eligible)

        non_asian_student = {"nationality": "Brazil"}
        result = checker.check_eligibility(scholarship, non_asian_student)
        assert result.is_eligible is False
        assert any("region" in r.lower() for r in result.reasons_ineligible)

    def test_degree_aliases(self, checker):
        """Test that degree aliases are matched correctly."""
        scholarship = {
            "id": "test",
            "eligibility_criteria": {
                "parsed_criteria": [
                    {"criterion_type": "degree_level", "criterion_value": "master", "is_mandatory": True},
                ]
            },
        }

        for degree in ["master", "masters", "MS", "MSc", "graduate"]:
            result = checker.check_eligibility(scholarship, {"degree_type": degree})
            assert result.is_eligible is True, f"Failed for degree: {degree}"

    def test_language_test_matching(self, checker):
        """Test language test score comparison."""
        scholarship = {
            "id": "test",
            "eligibility_criteria": {
                "parsed_criteria": [
                    {"criterion_type": "language_test", "criterion_value": "IELTS 7.0", "is_mandatory": True},
                ]
            },
        }

        passing_student = {"language_test": "IELTS 7.5"}
        result = checker.check_eligibility(scholarship, passing_student)
        assert result.is_eligible is True

        failing_student = {"language_test": "IELTS 6.5"}
        result = checker.check_eligibility(scholarship, failing_student)
        assert result.is_eligible is False

        wrong_test = {"language_test": "TOEFL 100"}
        result = checker.check_eligibility(scholarship, wrong_test)
        assert result.is_eligible is False
        assert any("TOEFL" in r for r in result.reasons_ineligible)

    def test_optional_criteria_not_blocking(self, checker):
        """Test that optional criteria don't block eligibility."""
        scholarship = {
            "id": "test",
            "eligibility_criteria": {
                "parsed_criteria": [
                    {"criterion_type": "min_gpa", "criterion_value": "3.5", "is_mandatory": True},
                    {"criterion_type": "nationality", "criterion_value": "USA", "is_mandatory": False},
                ]
            },
        }

        student = {"gpa": 3.8, "nationality": "India"}
        result = checker.check_eligibility(scholarship, student)

        assert result.is_eligible is True

    def test_to_dict(self, checker, full_scholarship, eligible_student):
        """Test that result can be converted to dict for API response."""
        result = checker.check_eligibility(full_scholarship, eligible_student)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "is_eligible" in result_dict
        assert "reasons_eligible" in result_dict
        assert "reasons_ineligible" in result_dict
        assert "missing_info" in result_dict
        assert "confidence" in result_dict
        assert isinstance(result_dict["confidence"], float)

    def test_confidence_calculation(self, checker):
        """Test confidence varies based on completeness of information."""
        scholarship = {
            "id": "test",
            "eligibility_criteria": {
                "parsed_criteria": [
                    {"criterion_type": "min_gpa", "criterion_value": "3.5", "is_mandatory": True},
                    {"criterion_type": "nationality", "criterion_value": "India", "is_mandatory": True},
                ]
            },
        }

        complete_student = {"gpa": 3.8, "nationality": "India"}
        result_complete = checker.check_eligibility(scholarship, complete_student)

        incomplete_student = {"gpa": 3.8}
        result_incomplete = checker.check_eligibility(scholarship, incomplete_student)

        assert result_complete.confidence >= result_incomplete.confidence
