"""Tests for Scrapy pipeline validation."""

import pytest
from scrapy.exceptions import DropItem

from app.crawlers.scrapy.pipelines import ValidateScholarshipPipeline


def test_validate_valid_item():
    pipeline = ValidateScholarshipPipeline()
    item = {
        "name": "DAAD Scholarship",
        "source_url": "https://daad.de/scholarship",
        "funding_amount": "50000",
    }
    result = pipeline.process_item(item, spider=None)
    assert result["funding_amount"] == 50000.0


def test_validate_missing_name():
    pipeline = ValidateScholarshipPipeline()
    item = {"source_url": "https://example.com"}
    with pytest.raises(DropItem, match="name"):
        pipeline.process_item(item, spider=None)


def test_validate_missing_source_url():
    pipeline = ValidateScholarshipPipeline()
    item = {"name": "DAAD Scholarship"}
    with pytest.raises(DropItem, match="source_url"):
        pipeline.process_item(item, spider=None)


def test_validate_invalid_funding_amount():
    pipeline = ValidateScholarshipPipeline()
    item = {
        "name": "DAAD Scholarship",
        "source_url": "https://example.com",
        "funding_amount": "not_a_number",
    }
    result = pipeline.process_item(item, spider=None)
    assert result["funding_amount"] is None
