"""LLM service with primary/fallback provider and structured extraction."""

import time
from typing import Any, Optional

from app.config import settings
from app.core.logging import get_logger
from app.llm.anthropic_client import call_anthropic
from app.llm.openai_client import call_openai
from app.llm.prompts import (
    get_eligibility_parsing_prompt,
    get_field_classification_prompt,
    get_scholarship_extraction_prompt,
)
from app.llm.schemas import ExtractedScholarshipData, FieldClassification, ParsedEligibilityCriteria
from app.models.linking import LLMExtractionResult
from app.utils.exceptions import LLMExtractionError

logger = get_logger(__name__)

_PRICING = {
    "openai": {"input": 0.15, "output": 0.60},
    "anthropic": {"input": 3.0, "output": 15.0},
}


class LLMService:
    """Orchestrates LLM calls with primary -> fallback provider logic."""

    async def extract_scholarship(self, page_text: str, source_url: str) -> LLMExtractionResult:
        """Extract structured scholarship data from page text using LLM.

        Tries OpenAI first; falls back to Anthropic on failure.
        """
        runtime_context: dict[str, Any] = {
            "source_url": source_url,
            "text_length": len(page_text),
        }
        system_prompt = get_scholarship_extraction_prompt(context=runtime_context, fmt="text")
        user_content = f"SOURCE URL: {source_url}\n\nPAGE CONTENT:\n{page_text}"

        start = time.perf_counter()
        fallback_reason: Optional[str] = None

        try:
            if settings.OPENAI_API_KEY:
                result = await call_openai(system_prompt, user_content)
                scholarship = ExtractedScholarshipData(**result["content"])
                latency = int((time.perf_counter() - start) * 1000)
                return LLMExtractionResult(
                    extracted_data=scholarship.model_dump(),
                    provider=result["provider"],
                    model=result["model"],
                    input_tokens=result["input_tokens"],
                    output_tokens=result["output_tokens"],
                    latency_ms=latency,
                    fallback_used=False,
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("openai_extraction_failed", error=str(exc))
            fallback_reason = f"OpenAI failed: {exc}"

        try:
            if settings.ANTHROPIC_API_KEY:
                result = await call_anthropic(system_prompt, user_content)
                scholarship = ExtractedScholarshipData(**result["content"])
                latency = int((time.perf_counter() - start) * 1000)
                return LLMExtractionResult(
                    extracted_data=scholarship.model_dump(),
                    provider=result["provider"],
                    model=result["model"],
                    input_tokens=result["input_tokens"],
                    output_tokens=result["output_tokens"],
                    latency_ms=latency,
                    fallback_used=True,
                    fallback_reason=fallback_reason,
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("anthropic_extraction_failed", error=str(exc))
            raise LLMExtractionError(f"Both LLM providers failed. Last error: {exc}") from exc

        raise LLMExtractionError("No LLM API key configured")

    async def parse_eligibility(self, eligibility_text: str) -> list[dict[str, Any]]:
        """Parse natural language eligibility criteria into structured entries."""
        system_prompt = get_eligibility_parsing_prompt(fmt="text")
        user_content = f"ELIGIBILITY TEXT:\n{eligibility_text}"

        try:
            if settings.OPENAI_API_KEY:
                result = await call_openai(system_prompt, user_content)
                parsed = ParsedEligibilityCriteria(**result["content"])
                return [c.model_dump() for c in parsed.criteria]
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("openai_eligibility_parsing_failed", error=str(exc))

        try:
            if settings.ANTHROPIC_API_KEY:
                result = await call_anthropic(system_prompt, user_content)
                parsed = ParsedEligibilityCriteria(**result["content"])
                return [c.model_dump() for c in parsed.criteria]
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("anthropic_eligibility_parsing_failed", error=str(exc))

        return []

    async def classify_field(self, scholarship_name: str, description: str | None = None) -> dict[str, Any]:
        """Classify a scholarship into a standard field and category."""
        system_prompt = get_field_classification_prompt(fmt="text")
        user_content = f"SCHOLARSHIP NAME: {scholarship_name}"
        if description:
            user_content += f"\n\nDESCRIPTION:\n{description}"

        try:
            if settings.OPENAI_API_KEY:
                result = await call_openai(system_prompt, user_content)
                classification = FieldClassification(**result["content"])
                return classification.model_dump()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("openai_classification_failed", error=str(exc))

        try:
            if settings.ANTHROPIC_API_KEY:
                result = await call_anthropic(system_prompt, user_content)
                classification = FieldClassification(**result["content"])
                return classification.model_dump()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("anthropic_classification_failed", error=str(exc))

        return {"field": scholarship_name, "field_category": None, "confidence": 0.0}

    @staticmethod
    def calculate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost in USD based on token counts."""
        pricing = _PRICING.get(provider, {"input": 0.0, "output": 0.0})
        return (input_tokens * pricing["input"] / 1_000_000) + (output_tokens * pricing["output"] / 1_000_000)
