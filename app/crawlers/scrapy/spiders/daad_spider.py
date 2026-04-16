"""Scrapy spider for DAAD scholarships using static JS data plus detail enrichment."""

from __future__ import annotations

import ast
import html
import json
import re
from typing import Any

import scrapy

from app.crawlers.parsers.html_parser import extract_page_text


class DAADSpider(scrapy.Spider):
    name = "daad_spider"
    allowed_domains = ["daad.de", "www2.daad.de"]
    start_urls = ["https://www2.daad.de/bundles/daadstipendiendatenbanklsh/data/a/js/scholarships.js"]
    detail_url_template = (
        "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/?detail={}"
    )
    TITLE_KEYS = (
        "programmnameEn",
        "langnameEn",
        "nameEn",
        "programmnameDe",
        "langnameDe",
        "nameDe",
        "title",
        "programme",
        "program",
        "name",
        "label",
        "shorttitle",
        "programname",
    )
    DESCRIPTION_KEYS = (
        "description",
        "programme_description",
        "program_description",
        "programmedescription",
        "programmeDescription",
        "programDescription",
        "objective",
        "teaser",
        "summary",
        "excerpt",
        "text",
    )
    DEADLINE_KEYS = (
        "deadline",
        "deadline_text",
        "application_deadline",
        "applicationdeadline",
        "applicationDeadline",
        "closing_date",
        "closingdate",
    )
    ELIGIBILITY_KEYS = (
        "eligibility",
        "target_group",
        "targetgroup",
        "targetGroup",
        "requirements",
        "application_requirements",
        "applicationrequirements",
        "applicationRequirements",
        "academic_requirements",
        "academicrequirements",
        "academicRequirements",
        "who_can_apply",
        "whoCanApply",
    )
    AMOUNT_KEYS = (
        "amount",
        "funding_amount",
        "fundingamount",
        "fundingAmount",
        "grant",
        "stipend",
        "scholarship_value",
        "scholarshipvalue",
        "scholarshipValue",
        "value",
    )
    GENERIC_TITLES = {
        "finding scholarships",
        "scholarship database",
        "daad scholarship",
    }

    def parse(self, response):
        self.logger.info("daad_listing_loaded url=%s", response.url)
        records = self._extract_records_from_js(response.text)
        if not records:
            self.logger.error("daad_records_not_found preview=%r", response.text[:300])
            return

        self.logger.info("daad_records_extracted count=%s", len(records))
        for record in records:
            scholarship = self._build_partial_scholarship(record)
            detail_id = scholarship.get("detail_id")
            if not detail_id and self._is_placeholder_scholarship(scholarship):
                self.logger.debug("daad_placeholder_skipped record=%r", record)
                continue
            if detail_id and self._needs_detail_enrichment(scholarship):
                yield scrapy.Request(
                    url=self.detail_url_template.format(detail_id),
                    callback=self.parse_scholarship_page,
                    meta={"scholarship_seed": scholarship},
                )
                continue

            scholarship.pop("detail_id", None)
            yield scholarship

    @classmethod
    def _extract_records_from_js(cls, body: str) -> list[dict[str, Any]]:
        payload = cls._extract_array_payload(body)
        if payload:
            for loader in (json.loads, cls._load_js_literal):
                try:
                    data = loader(payload)
                except (ValueError, SyntaxError):
                    continue
                if isinstance(data, list):
                    return [item for item in data if isinstance(item, dict)]

        return cls._extract_records_by_regex(body)

    @staticmethod
    def _extract_array_payload(body: str) -> str | None:
        anchors = ("TAFFY(", "scholarships =")
        for anchor in anchors:
            anchor_index = body.find(anchor)
            if anchor_index == -1:
                continue

            start = body.find("[", anchor_index)
            if start == -1:
                continue

            payload = DAADSpider._extract_balanced_array(body, start)
            if payload:
                return payload

        start = body.find("[")
        return DAADSpider._extract_balanced_array(body, start) if start != -1 else None

    @staticmethod
    def _extract_balanced_array(body: str, start: int) -> str | None:
        depth = 0
        quote: str | None = None
        escaped = False

        for index in range(start, len(body)):
            char = body[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue

            if char in {"'", '"'}:
                quote = char
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return body[start : index + 1]

        return None

    @staticmethod
    def _load_js_literal(payload: str) -> Any:
        normalized = re.sub(r"\btrue\b", "True", payload)
        normalized = re.sub(r"\bfalse\b", "False", normalized)
        normalized = re.sub(r"\bnull\b", "None", normalized)
        return ast.literal_eval(normalized)

    @staticmethod
    def _extract_records_by_regex(body: str) -> list[dict[str, Any]]:
        ids = []
        seen = set()
        for match in re.findall(r'["\']?id["\']?\s*:\s*["\']?(\d{8})["\']?', body):
            if match not in seen:
                seen.add(match)
                ids.append({"id": match})
        return ids

    def _build_partial_scholarship(self, record: dict[str, Any]) -> dict[str, Any]:
        detail_id = self._extract_detail_id(record)
        title = self._pick_first(record, *self.TITLE_KEYS)
        description = self._pick_first(record, *self.DESCRIPTION_KEYS)
        deadline = self._pick_first(record, *self.DEADLINE_KEYS)
        eligibility = self._pick_first(record, *self.ELIGIBILITY_KEYS)

        if not deadline:
            deadline = self._extract_deadline(" ".join(str(value) for value in record.values()))

        amount_text = self._pick_first(record, *self.AMOUNT_KEYS)
        funding_amount = self._extract_amount(amount_text or " ".join(str(value) for value in record.values()))

        return {
            "name": title.strip() if isinstance(title, str) else f"DAAD Scholarship {detail_id or ''}".strip(),
            "provider": "DAAD",
            "source_url": self.detail_url_template.format(detail_id) if detail_id else self.start_urls[0],
            "description": self._normalize_text(description),
            "funding_amount": funding_amount,
            "currency": "EUR",
            "deadline": self._normalize_text(deadline),
            "eligibility_text": self._normalize_text(eligibility),
            "spider_name": self.name,
            "detail_id": detail_id,
        }

    @staticmethod
    def _pick_first(record: dict[str, Any], *keys: str) -> str | None:
        lowered = {str(key).lower(): value for key, value in record.items()}
        for key in keys:
            value = lowered.get(key.lower())
            if value not in (None, "", []):
                return str(value)
        return None

    @staticmethod
    def _normalize_text(value: Any) -> str | None:
        if value is None:
            return None
        text = html.unescape(re.sub(r"\s+", " ", str(value))).strip()
        return text or None

    @staticmethod
    def _extract_detail_id(record: dict[str, Any]) -> str | None:
        for key in (
            "sapprogid",
            "sapobjid",
            "programmeid",
            "detail",
            "detail_id",
            "id",
        ):
            for record_key, value in record.items():
                if str(record_key).lower() == key and value:
                    match = re.search(r"(\d{8})", str(value))
                    if match:
                        return match.group(1)

        for value in record.values():
            match = re.search(r"((?:10|20|50)\d{6})", str(value))
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _needs_detail_enrichment(scholarship: dict[str, Any]) -> bool:
        return not all(
            [
                scholarship.get("description"),
                scholarship.get("deadline"),
                scholarship.get("eligibility_text"),
            ]
        )

    @staticmethod
    def _is_placeholder_scholarship(scholarship: dict[str, Any]) -> bool:
        """Return True for static-list placeholders that cannot be stored usefully."""
        return (
            scholarship.get("name") == "DAAD Scholarship"
            and not scholarship.get("description")
            and not scholarship.get("eligibility_text")
            and not scholarship.get("deadline")
        )

    @staticmethod
    def _extract_deadline(text):
        match = re.search(
            r"(Application deadline|Deadline)[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            text,
            re.IGNORECASE,
        )
        return match.group(2).strip() if match else None

    @staticmethod
    def _extract_amount(text):
        if not text:
            return None

        match = re.search(r"(?:EUR|[Ee]uro)s?\s*([\d][\d,]*(?:\.\d{2})?)", text)
        if not match:
            match = re.search(r"([\d][\d,]*(?:\.\d{2})?)\s*(?:EUR|[Ee]uro)s?", text)
        if not match:
            return None

        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _extract_eligibility_text(response):
        sections = response.xpath(
            "//h2[contains(translate(., 'ELIGIBILITY', 'eligibility'), 'eligibility') "
            "or contains(translate(., 'WHO CAN APPLY', 'who can apply'), 'who can apply')]"
            "/following-sibling::*[self::p or self::ul][position() <= 3]//text()"
        ).getall()
        return " ".join(text.strip() for text in sections if text.strip())

    def parse_scholarship_page(self, response):
        self.logger.info("daad_detail_loaded url=%s", response.url)
        seed = dict(response.meta.get("scholarship_seed") or {})
        clean_text = extract_page_text(response.text)
        seed_title = seed.get("name")
        title = seed_title if seed_title and seed_title.lower() not in self.GENERIC_TITLES else None
        title = title or self._extract_detail_title(response) or self._derive_title_from_text(clean_text)
        title = title or "DAAD Scholarship"
        description = self._extract_detail_description(response) or clean_text or seed.get("description")

        yield {
            "name": title,
            "provider": "DAAD",
            "source_url": response.url,
            "description": description,
            "funding_amount": self._extract_amount(clean_text) or seed.get("funding_amount"),
            "currency": "EUR",
            "deadline": self._extract_deadline(clean_text) or seed.get("deadline"),
            "eligibility_text": self._extract_eligibility_text(response) or seed.get("eligibility_text"),
            "spider_name": self.name,
        }

    def _extract_detail_title(self, response) -> str | None:
        candidates = response.xpath(
            "//div[contains(@class, 'content')]//h1/text() | "
            "//div[contains(@class, 'content')]//h2/text() | "
            "//h1/text() | //h2[contains(@class, 'mb-0')]/text() | //title/text()"
        ).getall()
        for candidate in candidates:
            text = self._normalize_text(candidate)
            if not text or text.lower() in self.GENERIC_TITLES:
                continue
            title = re.sub(r"\s*(?:[\u2022-])\s*DAAD.*$", "", text).strip()
            if title and title.lower() not in self.GENERIC_TITLES:
                return title
        return None

    @classmethod
    def _derive_title_from_text(cls, text: str) -> str | None:
        """Derive a DAAD scholarship title from page text when headings are generic."""
        clean = " ".join(text.split())
        patterns = [
            r"^(.+?)\s+-\s+DAAD\s+-",
            r"Search results\s+(.+?)\s+(?:[\u2022-]\s*)?DAAD\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, clean, re.IGNORECASE)
            if not match:
                continue
            title = cls._normalize_text(match.group(1))
            if title and title.lower() not in cls.GENERIC_TITLES:
                return title
        return None

    def _extract_detail_description(self, response) -> str | None:
        sections = response.xpath(
            "//h2[contains(translate(., 'PROGRAMME DESCRIPTIONOBJECTIVEWHAT CAN BE FUNDEDVALUE', "
            "'programme descriptionobjectivewhat can be fundedvalue'), 'programme description') "
            "or contains(translate(., 'PROGRAMME DESCRIPTIONOBJECTIVEWHAT CAN BE FUNDEDVALUE', "
            "'programme descriptionobjectivewhat can be fundedvalue'), 'objective') "
            "or contains(translate(., 'PROGRAMME DESCRIPTIONOBJECTIVEWHAT CAN BE FUNDEDVALUE', "
            "'programme descriptionobjectivewhat can be fundedvalue'), 'what can be funded') "
            "or contains(translate(., 'PROGRAMME DESCRIPTIONOBJECTIVEWHAT CAN BE FUNDEDVALUE', "
            "'programme descriptionobjectivewhat can be fundedvalue'), 'value')]"
            "/following-sibling::*[self::p or self::ul][position() <= 4]//text()"
        ).getall()
        text = self._normalize_text(" ".join(part.strip() for part in sections if part.strip()))
        return text

