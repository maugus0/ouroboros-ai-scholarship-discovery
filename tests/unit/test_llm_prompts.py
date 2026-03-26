"""Tests for LLM prompt building functions."""

import pytest

from app.llm.prompts import (
    get_eligibility_parsing_prompt,
    get_field_classification_prompt,
    get_scholarship_extraction_prompt,
)


def test_scholarship_extraction_prompt_json():
    result = get_scholarship_extraction_prompt(fmt="json")
    assert isinstance(result, str)
    assert "Scholarship Discovery Agent" in result


def test_scholarship_extraction_prompt_text():
    result = get_scholarship_extraction_prompt(fmt="text")
    assert isinstance(result, str)
    assert "AGENT IDENTITY" in result


def test_eligibility_parsing_prompt():
    result = get_eligibility_parsing_prompt(fmt="json")
    assert isinstance(result, str)
    assert "Scholarship Eligibility Criteria Parser" in result


def test_field_classification_prompt():
    result = get_field_classification_prompt(fmt="json")
    assert isinstance(result, str)
    assert "Academic Field Classifier" in result


def test_invalid_format_raises():
    with pytest.raises(ValueError, match="Unsupported prompt format"):
        get_scholarship_extraction_prompt(fmt="xml")


def test_prompt_with_context():
    context = {"source_url": "https://csc.edu.cn/scholarship", "text_length": 3000}
    result = get_scholarship_extraction_prompt(context=context, fmt="json")
    assert "source_url" in result
