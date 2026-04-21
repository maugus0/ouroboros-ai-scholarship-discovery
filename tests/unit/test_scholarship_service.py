"""Tests for scholarship storage and crawl orchestration behavior."""

import pytest

from app.services.crawl_service import CrawlService
from app.services.scholarship_service import ScholarshipService
from tests.fake_repos import FakeCrawlJobRepository, FakeEligibilityCriteriaRepository, FakeScholarshipRepository


@pytest.mark.asyncio
async def test_store_crawled_scholarship_upserts_by_source_url(sample_scholarship):
    service = ScholarshipService()
    fake_repo = FakeScholarshipRepository()
    service.scholarship_repo = fake_repo

    scholarship_id = await service.store_crawled_scholarship(sample_scholarship)
    updated_id = await service.store_crawled_scholarship(
        {
            **sample_scholarship,
            "name": "Updated Scholarship Name",
            "source_url": sample_scholarship["source_url"],
        }
    )

    stored = await fake_repo.get_by_id(scholarship_id)

    assert updated_id == scholarship_id
    assert stored["name"] == "Updated Scholarship Name"


@pytest.mark.asyncio
async def test_crawl_service_parses_and_stores_criteria():
    service = CrawlService()
    service.scholarship_service.scholarship_repo = FakeScholarshipRepository()
    service.crawl_job_repo = FakeCrawlJobRepository()
    service.criteria_repo = FakeEligibilityCriteriaRepository()

    async def fake_extract_scholarship(page_text, source_url):
        class Result:
            extracted_data = {
                "name": "Structured Scholarship",
                "provider": "DAAD",
                "description": page_text,
                "source_url": source_url,
                "currency": "EUR",
            }

        return Result()

    async def fake_parse_eligibility(text):
        assert "postgraduate" in text
        return [{"type": "degree_level", "value": "master", "is_mandatory": True}]

    service.llm_service.extract_scholarship = fake_extract_scholarship
    service.llm_service.parse_eligibility = fake_parse_eligibility

    scholarship_id = await service._process_scraped_item(
        {
            "name": "Raw Scholarship",
            "provider": "DAAD",
            "description": "Scholarship page body",
            "eligibility_text": "Open to postgraduate applicants.",
            "source_url": "https://example.com/scholarship",
        },
        active_programs=[],
    )

    criteria = await service.criteria_repo.get_by_scholarship_id(scholarship_id)

    assert len(criteria) == 1
    assert criteria[0]["criterion_type"] == "degree_level"
    assert criteria[0]["criterion_value"] == "master"
