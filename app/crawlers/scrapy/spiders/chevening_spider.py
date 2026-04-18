"""Scrapy spider for Chevening scholarships and fellowships."""

from __future__ import annotations

import html
import re
from typing import Any

import scrapy
from scrapy.http import Response

from app.crawlers.parsers.html_parser import extract_page_text


class CheveningSpider(scrapy.Spider):
    """Model Chevening as one global scholarship plus multiple fellowship programmes."""

    name = "chevening_spider"
    allowed_domains = ["chevening.org"]

    custom_settings = {
        "DOWNLOAD_DELAY": 3.0,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.5",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
    }

    def start_requests(self):
        yield scrapy.Request(
            url="https://www.chevening.org/scholarships/who-can-apply/",
            callback=self.parse_masters_base,
        )
        yield scrapy.Request(
            url="https://www.chevening.org/fellowships/find-a-programme/",
            callback=self.parse_fellowships_list,
        )

    def parse_masters_base(self, response: Response):
        self.logger.info(f"chevening_page_loaded url={response.url}")
        scholarship_seed = self._build_standard_scholarship(response)
        yield scrapy.Request(
            url="https://www.chevening.org/scholarships/apply/",
            callback=self.parse_masters_apply,
            meta={"scholarship_seed": scholarship_seed},
        )

    def parse_masters_apply(self, response: Response):
        self.logger.info(f"chevening_page_loaded url={response.url}")
        scholarship = dict(response.meta["scholarship_seed"])
        scholarship["application_requirements"] = self._build_application_requirements(response)
        yield scholarship

    def parse_fellowships_list(self, response: Response):
        self.logger.info(f"chevening_page_loaded url={response.url}")
        yield from self._follow_fellowship_links(response)

    def _build_standard_scholarship(self, response: Response) -> dict[str, Any]:
        clean_text = extract_page_text(response.text)
        return {
            "name": "Chevening Master's Scholarship (Global)",
            "provider": "UK Government (Chevening)",
            "source_url": "https://www.chevening.org/scholarships/",
            "description": clean_text,
            "funding_amount": self._extract_amount(clean_text),
            "currency": "GBP",
            "deadline": self._extract_deadline(clean_text),
            "eligibility_text": self._extract_eligibility_text(response) or clean_text[:1500],
            "application_requirements": {
                "application_route_url": "https://www.chevening.org/scholarships/apply/",
                "country_application_statuses": [],
            },
            "spider_name": self.name,
        }

    def _build_application_requirements(self, response: Response) -> dict[str, Any]:
        return {
            "application_route_url": response.url,
            "country_application_statuses": self._extract_country_application_statuses(response),
        }

    def _follow_fellowship_links(self, response: Response):
        links = response.css("main a::attr(href), article a::attr(href), .entry-content a::attr(href)").getall()
        valid_links = set()
        for link in links:
            absolute = response.urljoin(link)
            if not absolute.startswith("https://www.chevening.org/"):
                continue
            if "/fellowships/" not in absolute:
                continue
            if absolute.rstrip("/") == response.url.rstrip("/"):
                continue
            if absolute.rstrip("/").endswith("/find-a-programme"):
                continue
            valid_links.add(absolute)

        self.logger.info(f"found_chevening_fellowships count={len(valid_links)}")
        for detail_link in sorted(valid_links):
            yield scrapy.Request(url=detail_link, callback=self.parse_fellowship_detail)

    def parse_fellowship_detail(self, response: Response):
        self.logger.info(f"chevening_fellowship_loaded url={response.url}")
        clean_text = extract_page_text(response.text)
        title = response.xpath("//main//h1/text() | //div[contains(@class, 'content')]//h1/text() | //h1/text()").get()
        title = html.unescape(title.strip()) if title else "Chevening Fellowship"

        yield {
            "name": title,
            "provider": "UK Government (Chevening)",
            "source_url": response.url,
            "description": clean_text,
            "funding_amount": self._extract_amount(clean_text),
            "currency": "GBP",
            "deadline": self._extract_deadline(clean_text),
            "eligibility_text": self._extract_eligibility_text(response) or clean_text[:1500],
            "application_requirements": {
                "application_route_url": response.url,
                "country_application_statuses": [],
            },
            "spider_name": self.name,
        }

    @staticmethod
    def _extract_deadline(text: str) -> str | None:
        match = re.search(
            r"(Deadline|Applications close|closing date)[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            text,
            re.IGNORECASE,
        )
        return match.group(2).strip() if match else None

    @staticmethod
    def _extract_amount(text: str) -> float | None:
        match = re.search(r"(?:GBP|£|pounds?)\s?([\d,]+(?:\.\d{2})?)", text, re.IGNORECASE)
        return float(match.group(1).replace(",", "")) if match else None

    @staticmethod
    def _extract_eligibility_text(response: Response) -> str | None:
        sections = response.xpath(
            "//h2[contains(translate(., 'ELIGIBILITY', 'eligibility'), 'eligibility') "
            "or contains(translate(., 'WHO CAN APPLY', 'who can apply'), 'who can apply')]"
            "/following-sibling::*[self::p or self::ul][position() <= 5]//text()"
        ).getall()
        text = html.unescape(" ".join(t.strip() for t in sections if t.strip()))
        return text if text else None

    def _extract_country_application_statuses(self, response: Response) -> list[dict[str, str]]:
        statuses: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()

        option_nodes = response.xpath("//select//option[normalize-space(@value) != '']")
        for option in option_nodes:
            text = self._clean_text("".join(option.xpath(".//text()").getall()))
            route = response.urljoin(option.attrib.get("value", "").strip()) if option.attrib.get("value") else ""
            if not text:
                continue
            country = self._extract_country_name(text, route) or text
            status = self._infer_application_status(text)
            key = (country, status, route)
            if key not in seen:
                seen.add(key)
                statuses.append({"country": country, "status": status, "application_url": route})

        link_nodes = response.xpath(
            "//main//a[@href] | //article//a[@href] | //div[contains(@class, 'entry-content')]//a[@href]"
        )
        for link in link_nodes:
            text = self._clean_text("".join(link.xpath(".//text()").getall()))
            href = response.urljoin(link.attrib.get("href", "").strip())
            if not text or not href:
                continue
            if not re.search(r"\b(apply|application|open|closed|country|eligible)\b", text, re.IGNORECASE):
                continue
            country = self._extract_country_name(text, href)
            if not country:
                continue
            status = self._infer_application_status(text)
            key = (country, status, href)
            if key not in seen:
                seen.add(key)
                statuses.append({"country": country, "status": status, "application_url": href})

        return statuses

    @staticmethod
    def _extract_country_name(text: str, href: str) -> str | None:
        patterns = [
            r"for\s+([A-Z][A-Za-z' -]+)",
            r"from\s+([A-Z][A-Za-z' -]+)",
            r"([A-Z][A-Za-z' -]+)\s+(?:applications|application)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip(" -")

        slug_match = re.search(r"/([a-z-]+)/?$", href)
        if slug_match:
            slug = slug_match.group(1)
            if slug not in {"apply", "scholarships", "fellowships", "programme", "programmes"}:
                return slug.replace("-", " ").title()
        return None

    @staticmethod
    def _infer_application_status(text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("closed", "not open", "not available")):
            return "closed"
        if any(token in lowered for token in ("open", "available", "apply now")):
            return "open"
        return "unknown"

    @staticmethod
    def _clean_text(text: str) -> str:
        return html.unescape(re.sub(r"\s+", " ", text)).strip()
