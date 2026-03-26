"""BeautifulSoup helpers for extracting scholarship data from HTML pages.

Shared by Scrapy spiders and the on-demand crawler.
"""

import re
from typing import Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.utils.html_utils import clean_html_text

logger = get_logger(__name__)


def extract_page_text(html: str) -> str:
    """Extract and clean readable text from raw HTML."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    return clean_html_text(text)


def extract_basic_metadata(html: str) -> dict[str, Any]:
    """Regex-based fallback extraction when LLM is unavailable."""
    soup = BeautifulSoup(html, "lxml")
    result: dict[str, Any] = {
        "name": None,
        "provider": None,
        "funding_amount": None,
        "currency": "USD",
        "deadline": None,
        "description": None,
    }

    title_tag = soup.find("title")
    if title_tag:
        result["name"] = clean_html_text(title_tag.get_text())

    h1_tag = soup.find("h1")
    if h1_tag:
        result["name"] = clean_html_text(h1_tag.get_text())

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        result["description"] = meta_desc["content"][:500]

    result["deadline"] = _extract_deadline(html)
    result["funding_amount"] = _extract_funding_amount(html)

    return result


def scholarship_page_metadata(html: str, source_url: str, **extra: Any) -> dict[str, Any]:
    """Build basic scholarship metadata dict with ``source_url`` and optional spider fields."""
    metadata = extract_basic_metadata(html)
    metadata["source_url"] = source_url
    metadata.update(extra)
    return metadata


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all links from a page that might lead to scholarship detail pages."""
    soup = BeautifulSoup(html, "lxml")
    links = []

    scholarship_keywords = [
        "scholarship",
        "fellowship",
        "grant",
        "funding",
        "award",
        "bursary",
        "financial-aid",
        "financial_aid",
        "stipend",
    ]

    for anchor in soup.find_all("a", href=True):
        raw_href = anchor.get("href")
        if not raw_href or not isinstance(raw_href, str):
            continue
        href = raw_href.strip()
        text = anchor.get_text(strip=True).lower()

        if any(kw in href.lower() or kw in text for kw in scholarship_keywords):
            if href.startswith("/"):
                href = urljoin(base_url, href)
            if href.startswith("http"):
                links.append(href)

    return list(set(links))


def _extract_deadline(html: str) -> Optional[str]:
    """Attempt to extract application deadlines using regex patterns."""
    date_patterns = [
        r"deadline[:\s]*(\w+\s+\d{1,2},?\s+\d{4})",
        r"apply\s+by[:\s]*(\w+\s+\d{1,2},?\s+\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_funding_amount(html: str) -> Optional[float]:
    """Attempt to extract scholarship funding amounts using regex patterns."""
    patterns = [
        r"\$\s?([\d,]+(?:\.\d{2})?)\s*(?:per\s+year|annually|/year|award)?",
        r"(?:up\s+to|award\s+of|value\s+of)\s+\$\s?([\d,]+(?:\.\d{2})?)",
        r"USD\s?([\d,]+(?:\.\d{2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None
