"""Tests for the 4-dimension linking service (university, field, degree, geographic)."""

# Exercises small scoring helpers that are intentionally private.

# pylint: disable=protected-access

from app.services.linking_service import LinkingService


def test_university_match_exact():
    service = LinkingService()
    scholarship = {"provider": "MIT"}
    program = {"university_name": "MIT"}
    assert service._calc_university_match(scholarship, program) == 1.0


def test_university_match_partial():
    service = LinkingService()
    scholarship = {"provider": "Massachusetts Institute of Technology"}
    program = {"university_name": "MIT"}
    assert service._calc_university_match(scholarship, program) == 1.0


def test_university_match_substring():
    service = LinkingService()
    scholarship = {"provider": "MIT"}
    program = {"university_name": "MIT Department of CS"}
    assert service._calc_university_match(scholarship, program) == 1.0


def test_university_no_match():
    service = LinkingService()
    scholarship = {"provider": "Stanford"}
    program = {"university_name": "MIT"}
    assert service._calc_university_match(scholarship, program) == 0.0


def test_field_match_no_restriction():
    service = LinkingService()
    scholarship = {"eligibility_criteria": {}}
    program = {"field": "Computer Science"}
    assert service._calc_field_match(scholarship, program) == 1.0


def test_field_match_exact():
    service = LinkingService()
    scholarship = {"eligibility_criteria": {"field_of_study": ["Computer Science"]}}
    program = {"field": "Computer Science"}
    assert service._calc_field_match(scholarship, program) == 1.0


def test_field_match_from_parsed_criteria():
    service = LinkingService()
    scholarship = {
        "eligibility_criteria": {
            "parsed_criteria": [
                {
                    "criterion_type": "field_of_study",
                    "criterion_value": "Engineering, Computer Science",
                    "is_mandatory": True,
                }
            ]
        }
    }
    program = {"field": "Computer Science"}
    assert service._calc_field_match(scholarship, program) == 1.0


def test_degree_match_exact():
    service = LinkingService()
    scholarship = {"eligibility_criteria": {"degree_level": ["master"]}}
    program = {"degree_type": "master"}
    assert service._calc_degree_match(scholarship, program) == 1.0


def test_degree_match_from_comma_separated_criterion():
    service = LinkingService()
    scholarship = {
        "eligibility_criteria": {
            "parsed_criteria": [
                {"criterion_type": "degree_level", "criterion_value": "master, phd", "is_mandatory": True}
            ]
        }
    }
    program = {"degree_type": "master_coursework"}
    assert service._calc_degree_match(scholarship, program) == 1.0


def test_degree_no_restriction():
    service = LinkingService()
    scholarship = {"eligibility_criteria": {}}
    program = {"degree_type": "phd"}
    assert service._calc_degree_match(scholarship, program) == 1.0


def test_degree_mismatch():
    service = LinkingService()
    scholarship = {"eligibility_criteria": {"degree_level": ["phd"]}}
    program = {"degree_type": "master"}
    assert service._calc_degree_match(scholarship, program) == 0.0


def test_geographic_no_restriction():
    service = LinkingService()
    scholarship = {"eligibility_criteria": {}}
    program = {"country": "United States"}
    assert service._calc_geographic_match(scholarship, program) == 1.0


def test_geographic_macro_region_match():
    """Eligibility region macro-label (e.g. Asia) matches program country via region_mapping."""
    service = LinkingService()
    scholarship = {"eligibility_criteria": {"region": ["Asia"]}}
    program = {"country": "India"}
    assert service._calc_geographic_match(scholarship, program) == 1.0


def test_geographic_nationality_country_match_from_parsed_criteria():
    service = LinkingService()
    scholarship = {
        "eligibility_criteria": {
            "parsed_criteria": [
                {"criterion_type": "nationality", "criterion_value": "Yemen", "is_mandatory": True}
            ]
        }
    }
    program = {"country": "Yemen"}
    assert service._calc_geographic_match(scholarship, program) == 1.0


def test_geographic_macro_region_no_match():
    service = LinkingService()
    scholarship = {"eligibility_criteria": {"region": ["Asia"]}}
    program = {"country": "Brazil"}
    assert service._calc_geographic_match(scholarship, program) == 0.0


def test_determine_link_type():
    service = LinkingService()
    assert service._determine_link_type(1.0, 0.5, 0.3, 0.1) == "university"
    assert service._determine_link_type(0.0, 1.0, 0.3, 0.1) == "field"
    assert service._determine_link_type(0.0, 0.0, 1.0, 0.1) == "degree"
    assert service._determine_link_type(0.0, 0.0, 0.0, 1.0) == "geographic"


def test_calculate_composite_confidence_uses_weighted_average():
    service = LinkingService()
    confidence = service._calculate_composite_confidence(
        university_score=1.0,
        field_score=0.5,
        degree_score=1.0,
        geographic_score=0.0,
    )
    assert confidence == 0.80
