"""Tests for prompt template loading and building."""

import pytest

from app.utils.prompt_utils import build_prompt_json, build_prompt_text, load_prompt_template


def test_load_scholarship_extraction_template():
    template = load_prompt_template("scholarship_extraction_v1.json")
    assert "prompt_template" in template
    assert "base" in template["prompt_template"]


def test_load_eligibility_parsing_template():
    template = load_prompt_template("eligibility_parsing_v1.json")
    assert "prompt_template" in template


def test_load_field_classification_template():
    template = load_prompt_template("field_classification_v1.json")
    assert "prompt_template" in template


def test_load_nonexistent_template():
    with pytest.raises(FileNotFoundError):
        load_prompt_template("nonexistent_template.json")


def test_build_prompt_json_without_context():
    result = build_prompt_json("scholarship_extraction_v1.json")
    assert isinstance(result, str)
    assert "agent_identity" in result


def test_build_prompt_json_with_context():
    context = {"source_url": "https://example.com", "text_length": 5000}
    result = build_prompt_json("scholarship_extraction_v1.json", context)
    assert "source_url" in result
    assert "runtime_context" in result


def test_build_prompt_text():
    result = build_prompt_text("scholarship_extraction_v1.json")
    assert isinstance(result, str)
    assert "AGENT IDENTITY" in result
