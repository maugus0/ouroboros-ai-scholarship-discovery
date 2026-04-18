"""Crawl job management and execution."""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime
from typing import Any

from app.core.logging import get_logger
from app.crawlers.on_demand_crawler import crawl_scholarship_page, discover_scholarship_links
from app.repositories.mysql_crawl_job_repo import CrawlJobRepository
from app.repositories.mysql_eligibility_criteria_repo import EligibilityCriteriaRepository
from app.services.eligibility_criteria_builder import EligibilityCriteriaBuilder
from app.services.linking_service import LinkingService
from app.services.llm_service import LLMService
from app.services.scholarship_service import ScholarshipService
from app.utils.helpers import get_current_time_iso

logger = get_logger(__name__)


class CrawlService:
    """Manage crawl jobs and execute on-demand or source crawls."""

    _GENERIC_TITLES = {
        "finding scholarships",
        "scholarship database",
        "daad scholarship",
        "unknown scholarship",
    }

    def __init__(self):
        self.crawl_job_repo = CrawlJobRepository()
        self.scholarship_service = ScholarshipService()
        self.llm_service = LLMService()
        self.linking_service = LinkingService()
        self.criteria_repo = EligibilityCriteriaRepository()

    @staticmethod
    def _normalize_scholarship_payload(scraped_data: dict[str, Any]) -> dict[str, Any]:
        """Normalize crawler output into a scholarship storage payload."""
        payload = dict(scraped_data)
        payload.setdefault("name", "Unknown Scholarship")
        payload.setdefault("provider", "Unknown Provider")
        payload.setdefault("currency", None)
        payload.setdefault("source_url", "")
        payload.setdefault("description", "")
        derived_name = CrawlService._derive_title_from_text(payload.get("description", ""))
        if CrawlService._is_generic_title(payload.get("name")) and derived_name:
            payload["name"] = derived_name
        payload["crawled_at"] = payload.get("crawled_at") or get_current_time_iso()
        return payload

    @classmethod
    def _is_generic_title(cls, title: Any) -> bool:
        """Return True when a scraped title is a site-level heading, not a scholarship name."""
        if not isinstance(title, str):
            return True
        normalized = " ".join(title.split()).strip().lower()
        return not normalized or normalized in cls._GENERIC_TITLES

    @staticmethod
    def _derive_title_from_text(text: Any) -> str | None:
        """Derive a scholarship title from DAAD-like page text when the scraped title is generic."""
        if not isinstance(text, str) or not text.strip():
            return None

        clean = " ".join(text.split())
        candidates: list[str] = []

        search_match = re.search(
            r"(?:Search results|« Search results)\s+(.+?)\s+(?:[•-]\s*)?DAAD\b",
            clean,
            re.IGNORECASE,
        )
        if search_match:
            candidates.append(search_match.group(1))

        title_match = re.match(r"(.+?)\s+-\s+DAAD\s+-", clean)
        if title_match:
            candidates.append(title_match.group(1))

        for candidate in candidates:
            title = re.sub(r"\s+", " ", candidate).strip(" -•")
            if title and title.lower() not in CrawlService._GENERIC_TITLES:
                return title
        return None

    @staticmethod
    def _criteria_text_from_payload(payload: dict[str, Any]) -> str:
        """Extract the best free-text block for eligibility parsing."""
        if payload.get("eligibility_text"):
            return str(payload["eligibility_text"])

        criteria = payload.get("eligibility_criteria")
        if isinstance(criteria, str):
            return criteria
        if isinstance(criteria, dict):
            return "\n".join(f"{key}: {value}" for key, value in criteria.items())
        if isinstance(criteria, list):
            return "\n".join(str(item) for item in criteria)
        return ""

    @staticmethod
    def _merge_llm_extracted_data(
        payload: dict[str, Any],
        llm_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge LLM output into crawler payload without overwriting with empty values."""
        merged = dict(payload)
        for key, value in llm_data.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, (dict, list)) and not value:
                continue
            if key == "currency" and payload.get("currency"):
                continue
            merged[key] = value
        return merged

    @staticmethod
    def _truncate_description(description: str, max_length: int = 320) -> str:
        """Keep a readable summary-sized description for storage."""
        if not isinstance(description, str):
            return ""
        clean = " ".join(description.split())
        if len(clean) <= max_length:
            return clean
        truncated = clean[: max_length - 3].rsplit(" ", 1)[0].rstrip(" ,;:")
        return f"{truncated}..."

    @staticmethod
    def _normalize_currency(payload: dict[str, Any]) -> None:
        """Normalize common currency spellings into short codes without converting values."""
        currency = payload.get("currency")
        if not isinstance(currency, str):
            return
        lookup = {
            "euro": "EUR",
            "euros": "EUR",
            "eur": "EUR",
            "usd": "USD",
            "us dollar": "USD",
            "us dollars": "USD",
            "gbp": "GBP",
            "pound": "GBP",
            "pounds": "GBP",
        }
        normalized = lookup.get(currency.strip().lower())
        if normalized:
            payload["currency"] = normalized

    @staticmethod
    def _extract_amount_currency_from_text(page_text: str) -> tuple[float | None, str | None]:
        """Best-effort extraction of the primary funding amount and currency from raw text."""
        if not isinstance(page_text, str) or not page_text.strip():
            return None, None
        normalized = " ".join(page_text.split())
        patterns = [
            r"(?:monthly (?:scholarship payment|grant|payments?) of)\s+([\d,]+(?:\.\d+)?)\s*(EUR|USD|GBP|euros?|dollars?|pounds?)",
            r"(?:receive|receives?)\s+a\s+monthly\s+grant\s+of\s+([\d,]+(?:\.\d+)?)\s*(EUR|USD|GBP|euros?|dollars?|pounds?)",
            r"([\d,]+(?:\.\d+)?)\s*(EUR|USD|GBP|euros?|dollars?|pounds?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if not match:
                continue
            amount_text, currency_text = match.groups()
            try:
                amount = float(amount_text.replace(",", ""))
            except ValueError:
                continue
            currency = currency_text.upper()
            if currency.startswith("EURO"):
                currency = "EUR"
            elif currency.startswith("DOLLAR"):
                currency = "USD"
            elif currency.startswith("POUND"):
                currency = "GBP"
            return amount, currency
        return None, None

    @staticmethod
    def _extract_deadline_from_text(page_text: str) -> str | None:
        """Extract an explicit application deadline when a full date is present."""
        if not isinstance(page_text, str) or not page_text.strip():
            return None
        normalized = " ".join(page_text.split())
        patterns = [
            r"(?:deadline|application deadline|closing date|applications close(?: on)?)[:\s]+(\d{4}-\d{2}-\d{2})",
            r"(?:deadline|application deadline|closing date|applications close(?: on)?)[:\s]+([A-Z][a-z]+ \d{1,2}, \d{4})",
            r"(?:deadline|application deadline|closing date|applications close(?: on)?)[:\s]+(\d{1,2} [A-Z][a-z]+ \d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                return CrawlService._normalize_deadline(match.group(1))
        return None

    @staticmethod
    def _extract_section_text(
        page_text: str,
        start_markers: tuple[str, ...],
        stop_markers: tuple[str, ...],
    ) -> str | None:
        """Extract a readable section from flattened page text."""
        if not isinstance(page_text, str) or not page_text.strip():
            return None

        normalized = " ".join(page_text.split())
        lowered = normalized.lower()
        starts = []
        for marker in start_markers:
            marker_index = lowered.find(marker.lower())
            if marker_index != -1:
                starts.append((marker_index, marker))
        if not starts:
            return None

        start_index, marker = min(starts, key=lambda item: item[0])
        content_start = start_index + len(marker)
        stop_index = len(normalized)
        for stop_marker in stop_markers:
            marker_index = lowered.find(stop_marker.lower(), content_start)
            if marker_index != -1:
                stop_index = min(stop_index, marker_index)

        section = normalized[content_start:stop_index].strip(" :-")
        return section or None

    @staticmethod
    def _split_requirements(text: str | None, max_items: int = 12) -> list[str]:
        """Split a requirements section into compact list entries."""
        if not text:
            return []

        chunks = re.split(r"(?:\s*[;•]\s*|\s+(?=[A-Z][a-z]+(?:\s+[a-z]+){0,3}:))", text)
        requirements = []
        for chunk in chunks:
            item = " ".join(chunk.split()).strip(" ,-:")
            if not item or len(item) < 8:
                continue
            if item.lower().startswith(("please note", "technical requirements", "overview")):
                continue
            requirements.append(item)
            if len(requirements) >= max_items:
                break
        return requirements

    @staticmethod
    def _extract_structured_eligibility_from_text(page_text: str) -> dict[str, Any] | None:
        """Build eligibility_criteria from DAAD-like page sections when LLM omits it."""
        who_can_apply = CrawlService._extract_section_text(
            page_text,
            ("Who can apply?", "Target Group", "Target group"),
            (
                "What can be funded?",
                "Duration",
                "Scholarship Value",
                "Value",
                "Application requirements",
                "Application Procedure",
            ),
        )
        requirements = CrawlService._extract_section_text(
            page_text,
            ("What requirements must be met?", "Academic Requirements"),
            (
                "Application Papers",
                "Application Procedure",
                "Application Deadline",
                "Contact",
                "Please also take note",
            ),
        )
        if not requirements:
            requirements = CrawlService._extract_section_text(
                page_text,
                ("Application Requirements",),
                (
                    "Application Papers",
                    "Application Procedure",
                    "Application Deadline",
                    "Contact",
                    "Please also take note",
                ),
            )

        if not who_can_apply and not requirements:
            return None

        return {
            "who_can_apply": who_can_apply,
            "requirements": CrawlService._split_requirements(requirements),
            "raw_requirements": requirements,
        }

    @staticmethod
    def _extract_application_requirements_from_text(page_text: str) -> dict[str, Any] | None:
        """Build application_requirements from explicit documents/procedure sections."""
        papers = CrawlService._extract_section_text(
            page_text,
            ("Application Papers", "Application documents", "Documents to be uploaded"),
            (
                "Application Deadline",
                "Application requirements",
                "Application Procedure",
                "Contact",
                "Please note",
            ),
        )
        procedure = CrawlService._extract_section_text(
            page_text,
            ("Application Procedure", "Submitting an application"),
            (
                "Contact",
                "Contact and Consulting",
                "Please also take note",
                "Funded by",
            ),
        )
        deadline = CrawlService._extract_deadline_from_text(page_text)

        documents = CrawlService._split_requirements(papers)
        if not documents and not procedure and not deadline:
            return None

        return {
            "documents": documents,
            "application_portal": "DAAD portal" if "daad portal" in page_text.lower() else None,
            "deadline": deadline,
            "procedure": procedure,
        }

    @staticmethod
    def _normalize_deadline(value: Any) -> str | None:
        """Convert common LLM/scraper date formats into MySQL DATE format."""
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if not isinstance(value, str):
            return None

        text = " ".join(value.strip().strip(".").split())
        if not text:
            return None

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return text

        formats = (
            "%d %B %Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %d %Y",
            "%b %d %Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
        )
        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue

        return None

    @staticmethod
    def _finalize_extracted_payload(payload: dict[str, Any], page_text: str) -> dict[str, Any]:
        """Apply storage-oriented cleanup so rows stay readable and structured."""
        finalized = dict(payload)
        page_text = page_text if isinstance(page_text, str) else ""
        if finalized.get("description"):
            finalized["description"] = CrawlService._truncate_description(str(finalized["description"]))
        elif page_text:
            finalized["description"] = CrawlService._truncate_description(page_text)

        amount, currency = CrawlService._extract_amount_currency_from_text(page_text)
        if finalized.get("funding_amount") is None and amount is not None:
            finalized["funding_amount"] = amount
        if not finalized.get("currency") and currency:
            finalized["currency"] = currency
        if not finalized.get("deadline"):
            finalized["deadline"] = CrawlService._extract_deadline_from_text(page_text)
        else:
            finalized["deadline"] = CrawlService._normalize_deadline(finalized.get("deadline"))

        if not finalized.get("eligibility_criteria"):
            finalized["eligibility_criteria"] = CrawlService._extract_structured_eligibility_from_text(page_text)
        if not finalized.get("application_requirements"):
            finalized["application_requirements"] = CrawlService._extract_application_requirements_from_text(page_text)
        if not finalized.get("eligibility_text") and finalized.get("eligibility_criteria"):
            criteria = finalized["eligibility_criteria"]
            if isinstance(criteria, dict):
                finalized["eligibility_text"] = criteria.get("raw_requirements") or criteria.get("who_can_apply")

        CrawlService._normalize_currency(finalized)
        return finalized

    async def _store_parsed_criteria(self, scholarship_id: str, payload: dict[str, Any]) -> None:
        """Parse eligibility text with the LLM and store structured criteria."""
        criteria_text = self._criteria_text_from_payload(payload)
        deterministic_criteria = EligibilityCriteriaBuilder.build_from_scholarship(payload)
        parsed_criteria: list[dict[str, Any]] = []
        if criteria_text:
            parsed_criteria = await self.llm_service.parse_eligibility(criteria_text)

        criteria_to_store = deterministic_criteria + [
            {
                "criterion_type": criterion.get("type", "other"),
                "criterion_value": criterion.get("value", ""),
                "is_mandatory": criterion.get("is_mandatory", True),
            }
            for criterion in parsed_criteria
        ]
        criteria_to_store = EligibilityCriteriaBuilder._dedupe(criteria_to_store)
        if not criteria_to_store:
            return

        await self.criteria_repo.delete_by_scholarship_id(scholarship_id)
        for criterion in criteria_to_store:
            await self.criteria_repo.create_criterion(
                {
                    "scholarship_id": scholarship_id,
                    "criterion_type": criterion.get("criterion_type", "other"),
                    "criterion_value": criterion.get("criterion_value", ""),
                    "is_mandatory": criterion.get("is_mandatory", True),
                }
            )

        eligibility_payload = (
            payload.get("eligibility_criteria") if isinstance(payload.get("eligibility_criteria"), dict) else {}
        )
        eligibility_payload = dict(eligibility_payload)
        eligibility_payload["parsed_criteria"] = criteria_to_store
        await self.scholarship_service.store_crawled_scholarship(
            {
                "id": scholarship_id,
                "source_url": payload.get("source_url", ""),
                "name": payload.get("name", "Unknown Scholarship"),
                "provider": payload.get("provider", "Unknown Provider"),
                "currency": payload.get("currency"),
                "crawled_at": payload.get("crawled_at") or get_current_time_iso(),
                "eligibility_criteria": eligibility_payload,
            }
        )

    async def _process_scraped_item(
        self,
        scraped_data: dict[str, Any],
        active_programs: list[dict[str, Any]],
    ) -> str:
        """Process a scraped scholarship through extraction, persistence, and linking."""
        try:
            payload = self._normalize_scholarship_payload(scraped_data)
            page_text = payload.get("description", "")
            extracted = payload

            if page_text:
                try:
                    llm_result = await self.llm_service.extract_scholarship(
                        page_text=page_text,
                        source_url=payload["source_url"],
                    )
                    extracted = self._normalize_scholarship_payload(
                        self._merge_llm_extracted_data(payload, llm_result.extracted_data)
                    )
                    extracted["eligibility_text"] = payload.get("eligibility_text")
                    if not extracted.get("provider"):
                        extracted["provider"] = payload.get("provider", "Unknown Provider")
                    if not extracted.get("description"):
                        extracted["description"] = page_text
                except Exception as llm_exc:  # pylint: disable=broad-exception-caught
                    logger.error("llm_extraction_failed", source_url=payload["source_url"], error=str(llm_exc))
                    extracted = payload

            extracted = self._finalize_extracted_payload(extracted, page_text)

            scholarship_id = await self.scholarship_service.store_crawled_scholarship(extracted)
            await self._store_parsed_criteria(scholarship_id, extracted)

            if active_programs:
                for program in active_programs:
                    await self.linking_service.calculate_and_store_link(
                        scholarship_id=scholarship_id,
                        program_id=program["id"],
                        program_metadata=program,
                    )

            return scholarship_id
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "scraped_item_processing_failed",
                source_url=scraped_data.get("source_url", "unknown"),
                error=str(exc),
            )
            raise

    async def execute_on_demand_crawl(
        self,
        job_id: str,
        target_url: str,
        active_programs: list[dict[str, Any]] | None = None,
    ) -> None:
        """Execute an on-demand crawl for a specific URL."""
        await self.crawl_job_repo.update_status(job_id, "running")
        scholarships_crawled = 0
        scholarships_updated = 0

        try:
            scraped_data = await crawl_scholarship_page(target_url)
            if scraped_data:
                await self._process_scraped_item(scraped_data, active_programs or [])
                scholarships_crawled = 1
                scholarships_updated = 1

            await self.crawl_job_repo.update_status(
                job_id,
                "completed",
                scholarships_crawled=scholarships_crawled,
                scholarships_updated=scholarships_updated,
            )
            logger.info("on_demand_crawl_completed", job_id=job_id, url=target_url)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("on_demand_crawl_failed", job_id=job_id, error=str(exc))
            await self.crawl_job_repo.update_status(job_id, "failed", error_message=str(exc))

    async def execute_source_crawl(
        self,
        job_id: str,
        source_url: str,
        active_programs: list[dict[str, Any]] | None = None,
    ) -> None:
        """Execute a crawl over a listing page and track crawl job metrics."""
        await self.crawl_job_repo.update_status(job_id, "running")
        scholarships_crawled = 0
        scholarships_updated = 0

        try:
            links = await discover_scholarship_links(source_url)
            semaphore = asyncio.Semaphore(5)

            async def process_link(link: str) -> None:
                nonlocal scholarships_crawled, scholarships_updated
                try:
                    async with semaphore:
                        scraped_data = await crawl_scholarship_page(link)
                        if scraped_data:
                            await self._process_scraped_item(scraped_data, active_programs or [])
                            scholarships_crawled += 1
                            scholarships_updated += 1
                except Exception as link_exc:  # pylint: disable=broad-exception-caught
                    logger.warning("scholarship_page_crawl_failed", url=link, error=str(link_exc))

            await asyncio.gather(*(process_link(link) for link in links))

            await self.crawl_job_repo.update_status(
                job_id,
                "completed",
                scholarships_crawled=scholarships_crawled,
                scholarships_updated=scholarships_updated,
            )
            logger.info(
                "source_crawl_completed",
                job_id=job_id,
                source_url=source_url,
                links_discovered=len(links),
                scholarships_crawled=scholarships_crawled,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("source_crawl_failed", job_id=job_id, error=str(exc))
            await self.crawl_job_repo.update_status(job_id, "failed", error_message=str(exc))

    async def create_job(self, data: dict[str, Any]) -> str:
        """Create a crawl job record."""
        return await self.crawl_job_repo.create_job(data)

    async def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Return a crawl job by ID."""
        return await self.crawl_job_repo.get_by_id(job_id)

    async def list_jobs(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List crawl jobs with optional status filtering."""
        return await self.crawl_job_repo.list_jobs(limit=limit, offset=offset, status=status)
