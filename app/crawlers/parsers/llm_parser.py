"""LLM-assisted scholarship data extraction from HTML content."""

from typing import Any

from app.core.logging import get_logger
from app.crawlers.parsers.html_parser import extract_basic_metadata, extract_page_text
from app.services.llm_service import LLMService
from app.utils.exceptions import LLMExtractionError
from app.utils.html_utils import truncate_text

logger = get_logger(__name__)


async def extract_scholarship_metadata(html: str, source_url: str) -> dict[str, Any]:
    """Extract scholarship data with fallback to BeautifulSoup if LLM fails."""
    page_text = extract_page_text(html)
    truncated = truncate_text(page_text)

    try:
        llm_service = LLMService()
        result = await llm_service.extract_scholarship(truncated, source_url)
        logger.info("llm_extraction_succeeded", source_url=source_url)
        return result.extracted_data
    except LLMExtractionError:
        logger.warning("llm_extraction_failed_falling_back", source_url=source_url)
        return extract_basic_metadata(html)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("extraction_error", source_url=source_url, error=str(exc))
        return extract_basic_metadata(html)
