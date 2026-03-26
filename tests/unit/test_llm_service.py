"""Tests for LLM service (mocked — no real API calls)."""

import pytest

from app.services.llm_service import LLMService
from app.utils.exceptions import LLMExtractionError


@pytest.mark.asyncio
async def test_extract_scholarship_no_api_keys(monkeypatch):
    """With no API keys configured, extraction should raise."""
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.config.settings.ANTHROPIC_API_KEY", "")

    service = LLMService()
    with pytest.raises(LLMExtractionError, match="No LLM API key configured"):
        await service.extract_scholarship("Some page text", "https://example.com/scholarship")


def test_calculate_cost_openai():
    """OpenAI cost calculation should return a positive number."""
    cost = LLMService.calculate_cost("openai", 1000, 500)
    assert cost > 0
    assert isinstance(cost, float)


def test_calculate_cost_anthropic():
    """Anthropic cost should be higher than OpenAI for the same tokens."""
    openai_cost = LLMService.calculate_cost("openai", 1000, 500)
    anthropic_cost = LLMService.calculate_cost("anthropic", 1000, 500)
    assert anthropic_cost > openai_cost


def test_calculate_cost_unknown_provider():
    """Unknown provider should return 0.0."""
    cost = LLMService.calculate_cost("unknown_provider", 1000, 500)
    assert cost == 0.0
