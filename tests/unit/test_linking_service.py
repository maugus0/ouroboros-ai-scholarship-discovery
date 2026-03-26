"""Tests for the 4-dimension linking service."""

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
    assert service._calc_university_match(scholarship, program) == 0.0


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


def test_degree_match_exact():
    service = LinkingService()
    scholarship = {"eligibility_criteria": {"degree_level": ["master"]}}
    program = {"degree_type": "master"}
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


def test_determine_link_type():
    service = LinkingService()
    assert service._determine_link_type(1.0, 0.5, 0.3, 0.1) == "university"
    assert service._determine_link_type(0.0, 1.0, 0.3, 0.1) == "field"
    assert service._determine_link_type(0.0, 0.0, 1.0, 0.1) == "degree"
    assert service._determine_link_type(0.0, 0.0, 0.0, 1.0) == "geographic"
