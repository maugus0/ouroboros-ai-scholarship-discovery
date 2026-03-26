"""Tests for Pydantic models."""

from app.models.crawl import CrawlRequest, JobType
from app.models.linking import ConfidenceBreakdown, ProgramMetadata
from app.models.scholarship import ScholarshipSearchRequest, StudentProfileFilter


def test_scholarship_search_request_defaults():
    req = ScholarshipSearchRequest()
    assert req.max_results == 20
    assert req.page == 1
    assert req.student_profile is None
    assert req.program_ids == []


def test_scholarship_search_with_profile():
    req = ScholarshipSearchRequest(
        student_profile=StudentProfileFilter(
            gpa=3.8,
            nationality="India",
            field_of_study="Computer Science",
        ),
        max_results=10,
    )
    assert req.student_profile.gpa == 3.8
    assert req.student_profile.nationality == "India"
    assert req.max_results == 10


def test_student_profile_filter():
    profile = StudentProfileFilter(
        gpa=3.8,
        nationality="India",
        field_of_study="Computer Science",
        degree_type="master",
        language_test="IELTS 7.5",
    )
    assert profile.gpa == 3.8
    assert profile.gpa_scale == 4.0
    assert profile.nationality == "India"


def test_crawl_request_on_demand():
    req = CrawlRequest(
        job_type=JobType.ON_DEMAND,
        target_url="https://csc.edu.cn/scholarships",
    )
    assert req.job_type == JobType.ON_DEMAND
    assert req.target_url == "https://csc.edu.cn/scholarships"


def test_crawl_request_batch():
    req = CrawlRequest(job_type=JobType.BATCH)
    assert req.job_type == JobType.BATCH
    assert req.target_url is None


def test_program_metadata():
    meta = ProgramMetadata(
        program_id="prog-001",
        university_name="MIT",
        field="Computer Science",
        degree_type="master",
        country="United States",
    )
    assert meta.program_id == "prog-001"
    assert meta.university_name == "MIT"


def test_confidence_breakdown():
    breakdown = ConfidenceBreakdown(
        university_score=1.0,
        field_score=0.85,
        degree_score=1.0,
        geographic_score=1.0,
        total_confidence=0.97,
    )
    assert breakdown.total_confidence == 0.97
