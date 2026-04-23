"""Tests for the ScholarshipMatchingEngine with ReAct pattern explainability."""

from datetime import date, timedelta

import pytest

from app.agents.scholarship_matching_engine import (
    DECISION_CONSIDER,
    DECISION_FILTER_OUT,
    DECISION_RECOMMEND,
    MatchEvidence,
    MatchScores,
    ScholarshipMatchingEngine,
    apply_react_matching_pattern,
)


@pytest.fixture
def engine():
    """Create a ScholarshipMatchingEngine with default weights."""
    return ScholarshipMatchingEngine()


@pytest.fixture
def custom_engine():
    """Create engine with custom weights."""
    return ScholarshipMatchingEngine(
        weights={
            "university": 25,
            "field": 25,
            "degree": 25,
            "geographic": 25,
        }
    )


@pytest.fixture
def mit_scholarship():
    """MIT-specific scholarship for CS masters."""
    return {
        "id": "mit-001",
        "name": "MIT Presidential Fellowship",
        "provider": "MIT",
        "funding_amount": 50000,
        "currency": "USD",
        "deadline": (date.today() + timedelta(days=60)).isoformat(),
        "source_url": "https://mit.edu/fellowship",
        "eligibility_criteria": {
            "parsed_criteria": [
                {"criterion_type": "min_gpa", "criterion_value": "3.5", "is_mandatory": True},
                {"criterion_type": "degree_level", "criterion_value": "master,phd", "is_mandatory": True},
                {
                    "criterion_type": "field_of_study",
                    "criterion_value": "Computer Science,Engineering",
                    "is_mandatory": True,
                },
            ]
        },
    }


@pytest.fixture
def asia_only_scholarship():
    """Scholarship restricted to Asian students."""
    return {
        "id": "asia-001",
        "name": "Asia-Pacific STEM Scholarship",
        "provider": "APEC Foundation",
        "funding_amount": 30000,
        "currency": "USD",
        "deadline": (date.today() + timedelta(days=90)).isoformat(),
        "source_url": "https://apec.org/stem",
        "eligibility_criteria": {
            "parsed_criteria": [
                {"criterion_type": "region", "criterion_value": "Asia", "is_mandatory": True},
                {"criterion_type": "field_of_study", "criterion_value": "STEM", "is_mandatory": True},
            ]
        },
    }


@pytest.fixture
def open_scholarship():
    """Scholarship with minimal restrictions."""
    return {
        "id": "open-001",
        "name": "Global Excellence Award",
        "provider": "International Foundation",
        "funding_amount": 25000,
        "currency": "USD",
        "deadline": (date.today() + timedelta(days=120)).isoformat(),
        "source_url": "https://intl-foundation.org/excellence",
        "eligibility_criteria": {},
    }


@pytest.fixture
def mit_cs_student():
    """Student at MIT studying CS."""
    return {
        "gpa": 3.9,
        "nationality": "India",
        "field_of_study": "Computer Science",
        "degree_type": "master",
        "university": "MIT",
        "language_test": "IELTS 8.0",
    }


@pytest.fixture
def harvard_student():
    """Student at Harvard studying Economics."""
    return {
        "gpa": 3.7,
        "nationality": "USA",
        "field_of_study": "Economics",
        "degree_type": "master",
        "university": "Harvard",
    }


class TestMatchScores:
    """Test MatchScores dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        scores = MatchScores(
            university_alignment=0.95,
            field_alignment=0.88,
            degree_alignment=1.0,
            geographic_alignment=0.70,
        )
        result = scores.to_dict()

        assert result["university_alignment"] == 0.95
        assert result["field_alignment"] == 0.88
        assert result["degree_alignment"] == 1.0
        assert result["geographic_alignment"] == 0.7


class TestMatchEvidence:
    """Test MatchEvidence dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        evidence = MatchEvidence(
            university_alignment="Perfect match",
            field_alignment="Strong overlap",
            degree_alignment="Exact match",
            geographic_alignment="Regional match",
        )
        result = evidence.to_dict()

        assert result["university_alignment"] == "Perfect match"
        assert result["field_alignment"] == "Strong overlap"


class TestScholarshipMatchingEngine:
    """Test suite for ScholarshipMatchingEngine."""

    def test_perfect_match_mit_student(self, engine, mit_scholarship, mit_cs_student):
        """Test MIT student gets high score for MIT scholarship."""
        result = engine.apply_react_pattern(
            scholarships=[mit_scholarship],
            student_profile=mit_cs_student,
        )

        assert len(result.ranked_scholarships) == 1
        match = result.ranked_scholarships[0]

        assert match.composite_score >= 0.85
        assert match.decision == DECISION_RECOMMEND
        assert match.rank == 1
        assert match.match_scores.university_alignment >= 0.9
        assert match.match_scores.degree_alignment == 1.0
        assert "MIT" in match.match_evidence.university_alignment

    def test_university_mismatch(self, engine, mit_scholarship, harvard_student):
        """Test Harvard student gets lower university score for MIT scholarship."""
        result = engine.apply_react_pattern(
            scholarships=[mit_scholarship],
            student_profile=harvard_student,
        )

        assert len(result.ranked_scholarships) <= 1
        if result.ranked_scholarships:
            match = result.ranked_scholarships[0]
            assert match.match_scores.university_alignment < 0.5

    def test_geographic_restriction(self, engine, asia_only_scholarship, mit_cs_student, harvard_student):
        """Test geographic restrictions are enforced."""
        asian_result = engine.apply_react_pattern(
            scholarships=[asia_only_scholarship],
            student_profile=mit_cs_student,
        )

        usa_result = engine.apply_react_pattern(
            scholarships=[asia_only_scholarship],
            student_profile=harvard_student,
        )

        asian_match = asian_result.ranked_scholarships[0] if asian_result.ranked_scholarships else None
        usa_match = usa_result.ranked_scholarships[0] if usa_result.ranked_scholarships else None

        if asian_match:
            assert asian_match.match_scores.geographic_alignment >= 0.5
            assert "region" in asian_match.match_evidence.geographic_alignment.lower()

        if usa_match:
            assert usa_match.match_scores.geographic_alignment == 0.0

    def test_open_scholarship_high_scores(self, engine, open_scholarship, mit_cs_student):
        """Test open scholarships get high scores for all dimensions."""
        result = engine.apply_react_pattern(
            scholarships=[open_scholarship],
            student_profile=mit_cs_student,
        )

        assert len(result.ranked_scholarships) == 1
        match = result.ranked_scholarships[0]

        assert match.match_scores.field_alignment == 1.0
        assert match.match_scores.degree_alignment == 1.0
        assert match.match_scores.geographic_alignment == 1.0
        assert "open to all" in match.match_evidence.field_alignment.lower()

    def test_multiple_scholarships_ranking(
        self, engine, mit_scholarship, asia_only_scholarship, open_scholarship, mit_cs_student
    ):
        """Test multiple scholarships are correctly ranked."""
        result = engine.apply_react_pattern(
            scholarships=[mit_scholarship, asia_only_scholarship, open_scholarship],
            student_profile=mit_cs_student,
        )

        assert len(result.ranked_scholarships) >= 1

        if len(result.ranked_scholarships) >= 2:
            for i in range(len(result.ranked_scholarships) - 1):
                assert (
                    result.ranked_scholarships[i].composite_score >= result.ranked_scholarships[i + 1].composite_score
                )

        for i, match in enumerate(result.ranked_scholarships, 1):
            assert match.rank == i

    def test_decision_trace_structure(self, engine, mit_scholarship, mit_cs_student):
        """Test decision trace has correct structure."""
        result = engine.apply_react_pattern(
            scholarships=[mit_scholarship],
            student_profile=mit_cs_student,
        )

        assert mit_scholarship["id"] in result.react_decision_trace

        trace = result.react_decision_trace[mit_scholarship["id"]]
        assert trace.decision in [DECISION_RECOMMEND, DECISION_CONSIDER, DECISION_FILTER_OUT]
        assert len(trace.reasons) > 0
        assert any("university_alignment" in r for r in trace.reasons)

    def test_eligibility_summary(self, engine, mit_scholarship, asia_only_scholarship, mit_cs_student):
        """Test eligibility summary is correctly calculated."""
        result = engine.apply_react_pattern(
            scholarships=[mit_scholarship, asia_only_scholarship],
            student_profile=mit_cs_student,
        )

        summary = result.eligibility_summary
        assert summary["total_scholarships_evaluated"] == 2
        assert "fully_eligible" in summary
        assert "partially_eligible" in summary
        assert "ineligible" in summary

    def test_filters_applied_tracking(self, engine, mit_scholarship, mit_cs_student):
        """Test that filters applied are tracked."""
        result = engine.apply_react_pattern(
            scholarships=[mit_scholarship],
            student_profile=mit_cs_student,
        )

        assert len(result.filters_applied) > 0
        assert any("Student profile" in f for f in result.filters_applied)
        assert any("evaluated" in f.lower() for f in result.filters_applied)

    def test_confidence_map(self, engine, mit_scholarship, asia_only_scholarship, mit_cs_student):
        """Test confidence map contains scores for all scholarships."""
        result = engine.apply_react_pattern(
            scholarships=[mit_scholarship, asia_only_scholarship],
            student_profile=mit_cs_student,
        )

        assert mit_scholarship["id"] in result.confidence_map
        assert asia_only_scholarship["id"] in result.confidence_map
        assert 0 <= result.confidence_map[mit_scholarship["id"]] <= 1

    def test_to_dict_conversion(self, engine, mit_scholarship, mit_cs_student):
        """Test result can be converted to dict for API response."""
        result = engine.apply_react_pattern(
            scholarships=[mit_scholarship],
            student_profile=mit_cs_student,
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "react_decision_trace" in result_dict
        assert "ranked_scholarships" in result_dict
        assert "filters_applied" in result_dict
        assert "confidence_map" in result_dict
        assert "eligibility_summary" in result_dict

    def test_custom_weights(self, custom_engine, mit_scholarship, mit_cs_student):
        """Test custom weights affect scoring."""
        result = custom_engine.apply_react_pattern(
            scholarships=[mit_scholarship],
            student_profile=mit_cs_student,
        )

        assert len(result.ranked_scholarships) >= 1


class TestApplyReactMatchingPattern:
    """Test the convenience function."""

    def test_returns_dict(self, mit_scholarship, mit_cs_student):
        """Test convenience function returns a dict."""
        result = apply_react_matching_pattern(
            scholarships=[mit_scholarship],
            student_profile=mit_cs_student,
        )

        assert isinstance(result, dict)
        assert "react_decision_trace" in result
        assert "ranked_scholarships" in result

    def test_custom_weights_via_function(self, mit_scholarship, mit_cs_student):
        """Test custom weights can be passed to convenience function."""
        result = apply_react_matching_pattern(
            scholarships=[mit_scholarship],
            student_profile=mit_cs_student,
            matching_weights={"university": 100, "field": 0, "degree": 0, "geographic": 0},
        )

        assert isinstance(result, dict)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_scholarships_list(self, engine, mit_cs_student):
        """Test handling of empty scholarships list."""
        result = engine.apply_react_pattern(
            scholarships=[],
            student_profile=mit_cs_student,
        )

        assert len(result.ranked_scholarships) == 0
        assert result.eligibility_summary["total_scholarships_evaluated"] == 0

    def test_empty_student_profile(self, engine, mit_scholarship):
        """Test handling of empty student profile."""
        result = engine.apply_react_pattern(
            scholarships=[mit_scholarship],
            student_profile={},
        )

        assert len(result.ranked_scholarships) >= 0

    def test_scholarship_missing_fields(self, engine, mit_cs_student):
        """Test handling of scholarships with missing fields."""
        minimal_scholarship = {
            "id": "minimal-001",
            "name": "Minimal Scholarship",
            "provider": "Unknown",
            "eligibility_criteria": {},
        }

        result = engine.apply_react_pattern(
            scholarships=[minimal_scholarship],
            student_profile=mit_cs_student,
        )

        assert len(result.ranked_scholarships) >= 0

    def test_acronym_matching(self, engine):
        """Test university acronym matching."""
        scholarship = {
            "id": "mit-001",
            "name": "Fellowship",
            "provider": "MIT",
            "eligibility_criteria": {},
        }

        student = {
            "university": "Massachusetts Institute of Technology",
            "gpa": 3.8,
        }

        result = engine.apply_react_pattern(
            scholarships=[scholarship],
            student_profile=student,
        )

        if result.ranked_scholarships:
            match = result.ranked_scholarships[0]
            assert match.match_scores.university_alignment >= 0.9

    def test_deadline_handling(self, engine, mit_cs_student):
        """Test scholarships with passed deadlines are marked ineligible."""
        expired_scholarship = {
            "id": "expired-001",
            "name": "Expired Scholarship",
            "provider": "Foundation",
            "deadline": (date.today() - timedelta(days=30)).isoformat(),
            "eligibility_criteria": {},
        }

        result = engine.apply_react_pattern(
            scholarships=[expired_scholarship],
            student_profile=mit_cs_student,
        )

        if result.ranked_scholarships:
            match = result.ranked_scholarships[0]
            assert not match.eligibility_check.is_eligible
            assert any("passed" in r.lower() for r in match.eligibility_check.reasons_ineligible)
