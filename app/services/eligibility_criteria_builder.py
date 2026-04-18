"""Build database-ready eligibility criteria from stored scholarship JSON."""

from __future__ import annotations

import json
import re
from typing import Any


class EligibilityCriteriaBuilder:
    """Convert scholarship eligibility payloads into criteria table rows."""

    DEGREE_PATTERNS = (
        ("bachelor", r"\b(?:bachelor|undergraduate|undergraduates)\b"),
        ("master", r"\b(?:master|master's|masters|graduate students|graduates)\b"),
        ("phd", r"\b(?:phd|ph\.d|doctoral|doctorate|postdoc|postdoctoral)\b"),
    )
    FIELD_PATTERNS = (
        ("Engineering", r"\bengineering\b"),
        ("Computer Science", r"\b(?:computer science|informatics|artificial intelligence|AI)\b"),
        ("Natural Sciences", r"\b(?:natural sciences|science and technology|STEM)\b"),
        ("Humanities", r"\b(?:humanities|cultural studies|social sciences)\b"),
        ("Medicine", r"\b(?:medicine|medical|dentistry|veterinary)\b"),
        ("Agriculture", r"\b(?:agriculture|forestry)\b"),
    )
    NATIONALITY_PATTERNS = (
        r"\bmust be nationals? or permanent residents? of ([A-Z][A-Za-z .'-]+)",
        r"\bnationals? of ([A-Z][A-Za-z .'-]+)",
        r"\bpermanent residents? of ([A-Z][A-Za-z .'-]+)",
        r"\b([A-Z][A-Za-z .'-]+) citizenship\b",
    )
    NATIONALITY_REJECT_WORDS = (
        "applicant",
        "application",
        "current",
        "deadline",
        "document",
        "english",
        "german",
        "language",
        "motivation",
        "other",
        "proof",
        "research",
        "university",
    )
    REGION_KEYWORDS = {
        "Africa": r"\bAfrica|African\b",
        "Asia": r"\bAsia|Asian\b",
        "Europe": r"\bEurope|European\b",
        "South America": r"\bSouth America|Latin America\b",
        "North America": r"\bNorth America\b",
        "Oceania": r"\bOceania\b",
    }

    @classmethod
    def build_from_scholarship(cls, scholarship: dict[str, Any]) -> list[dict[str, Any]]:
        """Build criteria rows for one scholarship row/payload."""
        eligibility = cls._ensure_dict(scholarship.get("eligibility_criteria"))
        application = cls._ensure_dict(scholarship.get("application_requirements"))
        text_parts = [
            scholarship.get("name"),
            eligibility.get("who_can_apply"),
            " ".join(eligibility.get("requirements") or []),
            eligibility.get("raw_requirements"),
            " ".join(application.get("documents") or []),
            application.get("procedure"),
        ]
        text = " ".join(str(part) for part in text_parts if part)

        criteria: list[dict[str, Any]] = []
        cls._append(criteria, "other", eligibility.get("who_can_apply"), True)

        for requirement in eligibility.get("requirements") or []:
            cls._append(criteria, "other", requirement, True)

        cls._add_degree_levels(criteria, text)
        cls._add_nationalities(criteria, text)
        cls._add_regions(criteria, text)
        cls._add_fields(criteria, text)
        cls._add_language_tests(criteria, text)
        cls._add_min_gpa(criteria, text)
        cls._add_work_experience(criteria, text)

        return cls._dedupe(criteria)

    @staticmethod
    def _ensure_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    @staticmethod
    def _append(criteria: list[dict[str, Any]], criterion_type: str, value: Any, is_mandatory: bool) -> None:
        if value is None:
            return
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value if item)
        value = " ".join(str(value).split()).strip()
        if not value:
            return
        criteria.append(
            {
                "criterion_type": criterion_type,
                "criterion_value": value,
                "is_mandatory": is_mandatory,
            }
        )

    @classmethod
    def _add_degree_levels(cls, criteria: list[dict[str, Any]], text: str) -> None:
        levels = [label for label, pattern in cls.DEGREE_PATTERNS if re.search(pattern, text, re.IGNORECASE)]
        if levels:
            cls._append(criteria, "degree_level", levels, True)

    @classmethod
    def _add_fields(cls, criteria: list[dict[str, Any]], text: str) -> None:
        fields = [label for label, pattern in cls.FIELD_PATTERNS if re.search(pattern, text, re.IGNORECASE)]
        if fields:
            cls._append(criteria, "field_of_study", fields, True)

    @classmethod
    def _add_nationalities(cls, criteria: list[dict[str, Any]], text: str) -> None:
        values = []
        for pattern in cls.NATIONALITY_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1).strip(" .,;:")
                value = re.split(r"\s+(?:and|or|who|with|before|at)\b", value, maxsplit=1, flags=re.IGNORECASE)[0]
                if cls._looks_like_country_or_nationality(value):
                    values.append(value)
        if re.search(r"\bYemeni\b|\bYemenis\b", text, re.IGNORECASE):
            values.append("Yemen")
        if re.search(r"\bUkrainian citizenship\b|\bUkrainian graduate\b", text, re.IGNORECASE):
            values.append("Ukraine")
        if values:
            cls._append(criteria, "nationality", cls._unique(values), True)

    @classmethod
    def _looks_like_country_or_nationality(cls, value: str) -> bool:
        """Reject common false positives from long free-text requirements."""
        value = " ".join(value.split()).strip(" .,;:")
        if len(value) < 2 or len(value) > 50:
            return False
        words = value.split()
        if len(words) > 4:
            return False
        lowered = value.lower()
        if any(word in lowered for word in cls.NATIONALITY_REJECT_WORDS):
            return False
        if not re.match(r"^[A-Z][A-Za-z .'-]+$", value):
            return False
        return True

    @classmethod
    def _add_regions(cls, criteria: list[dict[str, Any]], text: str) -> None:
        regions = [region for region, pattern in cls.REGION_KEYWORDS.items() if re.search(pattern, text, re.IGNORECASE)]
        if regions:
            cls._append(criteria, "region", cls._unique(regions), False)

    @classmethod
    def _add_language_tests(cls, criteria: list[dict[str, Any]], text: str) -> None:
        for test in ("IELTS", "TOEFL"):
            pattern = rf"\b{test}\b[^\d]{{0,30}}(?:at least|minimum|score of)?\s*(\d+(?:\.\d+)?)"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                cls._append(criteria, "language_test", f"{test.upper()} {match.group(1)}", True)
        for match in re.finditer(r"\b([ABC][12])[- ]level\b", text, re.IGNORECASE):
            cls._append(criteria, "language_test", f"CEFR {match.group(1).upper()}", True)

    @classmethod
    def _add_min_gpa(cls, criteria: list[dict[str, Any]], text: str) -> None:
        match = re.search(r"\bGPA\b[^\d]{0,20}(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if match:
            cls._append(criteria, "min_gpa", match.group(1), True)

    @classmethod
    def _add_work_experience(cls, criteria: list[dict[str, Any]], text: str) -> None:
        match = re.search(r"(\d+\s+years?[^.]{0,80}(?:work|professional) experience)", text, re.IGNORECASE)
        if match:
            cls._append(criteria, "work_experience", match.group(1), True)

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            key = value.strip().lower()
            if key and key not in seen:
                seen.add(key)
                result.append(value.strip())
        return result

    @staticmethod
    def _dedupe(criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = set()
        result = []
        for criterion in criteria:
            key = (
                criterion["criterion_type"],
                criterion["criterion_value"].lower(),
                bool(criterion.get("is_mandatory", True)),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(criterion)
        return result
