"""On-demand web crawler using httpx + BeautifulSoup for targeted scraping.

Used for single-URL and listing-page discovery flows invoked by ``CrawlService``.
"""

import asyncio
import random
from typing import Any

import httpx
from fake_useragent import UserAgent

from app.config import settings
from app.core.logging import get_logger
from app.crawlers.parsers.html_parser import extract_links
from app.crawlers.parsers.llm_parser import extract_scholarship_metadata
from app.utils.html_utils import is_valid_url

logger = get_logger(__name__)

_ua = UserAgent(fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")


async def fetch_page(url: str, timeout: int = 30) -> str | None:
    """Fetch a single page with a randomised user agent and configurable delay."""
    if not is_valid_url(url):
        logger.warning("invalid_url", url=url)
        return None

    headers = {"User-Agent": _ua.random}

    delay = random.uniform(settings.MIN_CRAWL_DELAY_SECONDS, settings.MAX_CRAWL_DELAY_SECONDS)  # nosec B311
    await asyncio.sleep(delay)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            logger.info("page_fetched", url=url, status=response.status_code, size=len(response.text))
            return response.text
    except httpx.HTTPError as exc:
        logger.error("page_fetch_failed", url=url, error=str(exc))
        return None


async def crawl_scholarship_page(url: str) -> dict[str, Any] | None:
    """Fetch a scholarship page and extract metadata using LLM-assisted parsing."""
    html = await fetch_page(url)
    if html is None:
        return None

    metadata = await extract_scholarship_metadata(html, url)
    metadata["source_url"] = url
    return metadata


async def discover_scholarship_links(page_url: str) -> list[str]:
    """Crawl a scholarship listing page and discover individual scholarship links."""
    html = await fetch_page(page_url)
    if html is None:
        return []

    links = extract_links(html, page_url)
    logger.info("scholarship_links_discovered", url=page_url, count=len(links))
    return links
