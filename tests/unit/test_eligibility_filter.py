"""Tests for the eligibility filtering service."""

# Exercises strict matching helpers that are intentionally private.

# pylint: disable=protected-access

from app.services.eligibility_filter_service import EligibilityFilterService


def test_meets_gpa_criterion():
    service = EligibilityFilterService()
    profile = {"gpa": 3.8}
    criterion = {"criterion_type": "min_gpa", "criterion_value": "3.5", "is_mandatory": True}
    assert service._meets_criterion(profile, criterion) is True


def test_fails_gpa_criterion():
    service = EligibilityFilterService()
    profile = {"gpa": 3.0}
    criterion = {"criterion_type": "min_gpa", "criterion_value": "3.5", "is_mandatory": True}
    assert service._meets_criterion(profile, criterion) is False


def test_meets_nationality_criterion():
    service = EligibilityFilterService()
    profile = {"nationality": "India"}
    criterion = {"criterion_type": "nationality", "criterion_value": "India,China,Japan", "is_mandatory": True}
    assert service._meets_criterion(profile, criterion) is True


def test_fails_nationality_criterion():
    service = EligibilityFilterService()
    profile = {"nationality": "Brazil"}
    criterion = {"criterion_type": "nationality", "criterion_value": "India,China,Japan", "is_mandatory": True}
    assert service._meets_criterion(profile, criterion) is False


def test_meets_region_criterion():
    service = EligibilityFilterService()
    profile = {"nationality": "India"}
    criterion = {"criterion_type": "region", "criterion_value": "Asia", "is_mandatory": True}
    assert service._meets_criterion(profile, criterion) is True


def test_fails_region_criterion():
    service = EligibilityFilterService()
    profile = {"nationality": "Brazil"}
    criterion = {"criterion_type": "region", "criterion_value": "Asia", "is_mandatory": True}
    assert service._meets_criterion(profile, criterion) is False


def test_meets_field_criterion():
    service = EligibilityFilterService()
    profile = {"field_of_study": "Computer Science"}
    criterion = {
        "criterion_type": "field_of_study",
        "criterion_value": "Computer Science,Engineering",
        "is_mandatory": True,
    }
    assert service._meets_criterion(profile, criterion) is True


def test_meets_degree_criterion():
    service = EligibilityFilterService()
    profile = {"degree_type": "master"}
    criterion = {"criterion_type": "degree_level", "criterion_value": "master,phd", "is_mandatory": True}
    assert service._meets_criterion(profile, criterion) is True


def test_meets_language_criterion():
    service = EligibilityFilterService()
    profile = {"language_test": "IELTS 7.5"}
    criterion = {"criterion_type": "language_test", "criterion_value": "IELTS 7.0", "is_mandatory": True}
    assert service._meets_criterion(profile, criterion) is True


def test_fails_language_criterion():
    service = EligibilityFilterService()
    profile = {"language_test": "IELTS 6.0"}
    criterion = {"criterion_type": "language_test", "criterion_value": "IELTS 7.0", "is_mandatory": True}
    assert service._meets_criterion(profile, criterion) is False


def test_skips_non_mandatory():
    service = EligibilityFilterService()
    profile = {"gpa": 3.0}
    criteria = [
        {"criterion_type": "min_gpa", "criterion_value": "3.5", "is_mandatory": False},
    ]
    assert service._meets_all_mandatory(profile, criteria) is True


def test_nationality_in_region():
    assert EligibilityFilterService._nationality_in_region("India", "Asia") is True
    assert EligibilityFilterService._nationality_in_region("Brazil", "Asia") is False
    assert EligibilityFilterService._nationality_in_region("USA", "North America") is True
