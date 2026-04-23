"""4-Dimension Scholarship-Program Linking Service with Explainability.

Calculates confidence scores across university, field, degree, and geographic dimensions.
Geographic scoring uses :func:`app.utils.region_mapping.entity_matches_region`.

Now includes evidence strings for each dimension to support ReAct explainability.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional

from app.config import settings
from app.core.logging import get_logger
from app.repositories.mysql_link_repo import LinkRepository
from app.repositories.mysql_scholarship_repo import ScholarshipRepository
from app.utils.region_mapping import REGION_TO_COUNTRIES, entity_matches_region

logger = get_logger(__name__)


@dataclass
class DimensionScore:
    """Score with evidence for a single dimension."""

    score: float
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {"score": round(self.score, 3), "evidence": self.evidence}


@dataclass
class LinkMatchResult:
    """Complete match result with scores and evidence for all dimensions."""

    university_score: DimensionScore
    field_score: DimensionScore
    degree_score: DimensionScore
    geographic_score: DimensionScore
    composite_score: float
    link_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "university": self.university_score.to_dict(),
            "field": self.field_score.to_dict(),
            "degree": self.degree_score.to_dict(),
            "geographic": self.geographic_score.to_dict(),
            "composite_score": round(self.composite_score, 3),
            "link_type": self.link_type,
        }

    def get_match_metadata(self) -> dict[str, float]:
        """Get legacy match_metadata format for database storage."""
        return {
            "university_score": round(self.university_score.score, 3),
            "field_score": round(self.field_score.score, 3),
            "degree_score": round(self.degree_score.score, 3),
            "geographic_score": round(self.geographic_score.score, 3),
        }

    def get_evidence_metadata(self) -> dict[str, str]:
        """Get evidence strings for all dimensions."""
        return {
            "university_evidence": self.university_score.evidence,
            "field_evidence": self.field_score.evidence,
            "degree_evidence": self.degree_score.evidence,
            "geographic_evidence": self.geographic_score.evidence,
        }


class LinkingService:
    """Calculate and store 4-dimension scholarship-program links."""

    ACRONYM_STOPWORDS = {"and", "for", "of", "the", "to", "in"}

    def __init__(self):
        self.link_repo = LinkRepository()
        self.scholarship_repo = ScholarshipRepository()

    @staticmethod
    def _normalize_text(value: Any) -> str:
        """Lowercase and remove punctuation for lenient text matching."""
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    @staticmethod
    def _split_values(value: Any) -> list[str]:
        """Normalize comma/list/dict values into a flat list of strings."""
        if value in (None, "", [], {}):
            return []
        if isinstance(value, list):
            values: list[str] = []
            for item in value:
                values.extend(LinkingService._split_values(item))
            return values
        if isinstance(value, dict):
            return LinkingService._split_values(value.get("criterion_value") or value.get("value"))
        return [part.strip() for part in str(value).split(",") if part.strip()]

    @staticmethod
    def _eligibility_payload(scholarship: dict[str, Any]) -> dict[str, Any]:
        """Return eligibility JSON as a dict when available."""
        eligibility = scholarship.get("eligibility_criteria") or {}
        if isinstance(eligibility, dict):
            return eligibility
        return {}

    @staticmethod
    def _criterion_values(scholarship: dict[str, Any], criterion_type: str) -> list[str]:
        """Extract values from parsed_criteria first, then legacy flat JSON keys."""
        eligibility = LinkingService._eligibility_payload(scholarship)
        values: list[str] = []

        for criterion in eligibility.get("parsed_criteria") or []:
            if not isinstance(criterion, dict):
                continue
            if criterion.get("criterion_type") == criterion_type or criterion.get("type") == criterion_type:
                values.extend(LinkingService._split_values(criterion.get("criterion_value") or criterion.get("value")))

        if not values:
            values.extend(LinkingService._split_values(eligibility.get(criterion_type)))

        return LinkingService._unique_strings(values)

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        """Dedupe values case-insensitively while preserving original spelling."""
        seen = set()
        result = []
        for value in values:
            normalized = LinkingService._normalize_text(value)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(value)
        return result

    @classmethod
    def _acronym(cls, tokens: list[str]) -> str:
        """Build an acronym while ignoring common institution-name stopwords."""
        return "".join(token[0] for token in tokens if token and token not in cls.ACRONYM_STOPWORDS)

    async def calculate_and_store_link(
        self,
        scholarship_id: str,
        program_id: str,
        program_metadata: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Calculate 4-dimension confidence score and store link if >= threshold."""
        scholarship = await self.scholarship_repo.get_by_id(scholarship_id)
        if not scholarship:
            logger.warning("scholarship_not_found", scholarship_id=scholarship_id)
            return None

        university_score = self._calc_university_match(scholarship, program_metadata)
        field_score = self._calc_field_match(scholarship, program_metadata)
        degree_score = self._calc_degree_match(scholarship, program_metadata)
        geographic_score = self._calc_geographic_match(scholarship, program_metadata)

        confidence = self._calculate_composite_confidence(
            university_score=university_score,
            field_score=field_score,
            degree_score=degree_score,
            geographic_score=geographic_score,
        )

        if confidence < settings.MIN_LINK_CONFIDENCE_SCORE:
            logger.info(
                "link_below_threshold",
                confidence=f"{confidence:.3f}",
                threshold=settings.MIN_LINK_CONFIDENCE_SCORE,
            )
            return None

        link_type = self._determine_link_type(university_score, field_score, degree_score, geographic_score)

        match_metadata = {
            "university_score": round(university_score, 3),
            "field_score": round(field_score, 3),
            "degree_score": round(degree_score, 3),
            "geographic_score": round(geographic_score, 3),
        }

        link = await self.link_repo.create_or_update(
            scholarship_id=scholarship_id,
            program_id=program_id,
            link_type=link_type,
            confidence_score=round(confidence, 3),
            match_metadata=match_metadata,
        )

        logger.info(
            "link_created",
            scholarship_id=scholarship_id,
            program_id=program_id,
            confidence=f"{confidence:.3f}",
            link_type=link_type,
        )

        return link

    async def calculate_link_with_evidence(
        self,
        scholarship_id: str,
        program_metadata: dict[str, Any],
    ) -> Optional[LinkMatchResult]:
        """Calculate 4-dimension confidence score with evidence strings.

        This method returns full evidence for explainability without storing the link.

        Args:
            scholarship_id: Scholarship ID to match
            program_metadata: Program data (university_name, field, degree_type, country)

        Returns:
            LinkMatchResult with scores and evidence for all dimensions, or None if scholarship not found
        """
        scholarship = await self.scholarship_repo.get_by_id(scholarship_id)
        if not scholarship:
            logger.warning("scholarship_not_found", scholarship_id=scholarship_id)
            return None

        university_result = self._calc_university_match_with_evidence(scholarship, program_metadata)
        field_result = self._calc_field_match_with_evidence(scholarship, program_metadata)
        degree_result = self._calc_degree_match_with_evidence(scholarship, program_metadata)
        geographic_result = self._calc_geographic_match_with_evidence(scholarship, program_metadata)

        composite = self._calculate_composite_confidence(
            university_score=university_result.score,
            field_score=field_result.score,
            degree_score=degree_result.score,
            geographic_score=geographic_result.score,
        )

        link_type = self._determine_link_type(
            university_result.score,
            field_result.score,
            degree_result.score,
            geographic_result.score,
        )

        return LinkMatchResult(
            university_score=university_result,
            field_score=field_result,
            degree_score=degree_result,
            geographic_score=geographic_result,
            composite_score=composite,
            link_type=link_type,
        )

    def _calc_university_match_with_evidence(
        self,
        scholarship: dict[str, Any],
        program_metadata: dict[str, Any],
    ) -> DimensionScore:
        """Calculate university match with evidence string."""
        university = program_metadata.get("university_name", "")
        provider = scholarship.get("provider", "")
        scholarship_name = scholarship.get("name", "")

        if not university:
            return DimensionScore(0.0, "University not specified in program metadata")

        normalized_university = self._normalize_text(university)
        university_tokens = normalized_university.split()
        university_acronym = self._acronym(university_tokens)

        candidates = [(provider, "provider"), (scholarship_name, "scholarship name")]

        for candidate, source in candidates:
            normalized_candidate = self._normalize_text(candidate)
            if not normalized_candidate:
                continue

            if normalized_candidate == normalized_university:
                return DimensionScore(
                    1.0, f"Perfect match: Program at '{university}', scholarship {source} is '{candidate}'"
                )

            if normalized_candidate in normalized_university or normalized_university in normalized_candidate:
                score = 1.0 if source == "provider" else 0.85
                return DimensionScore(
                    score, f"Substring match: Program's '{university}' matches scholarship {source} '{candidate}'"
                )

            candidate_tokens = normalized_candidate.split()

            if (
                len(candidate_tokens) == 1
                and len(candidate_tokens[0]) <= 8
                and candidate_tokens[0] == university_acronym
            ):
                return DimensionScore(
                    1.0,
                    f"Acronym match: Program at '{university}' ({university_acronym}) matches {source} '{candidate}'",
                )

            if len(university_tokens) == 1 and len(university_tokens[0]) <= 8:
                candidate_acronym = self._acronym(candidate_tokens)
                if university_tokens[0] == candidate_acronym:
                    return DimensionScore(
                        1.0, f"Acronym match: Program at '{university}' matches {source} acronym ({candidate_acronym})"
                    )

            overlap = set(candidate_tokens) & set(university_tokens)
            if len(overlap) >= 2:
                score = 0.9 if source == "provider" else 0.75
                return DimensionScore(
                    score, f"Partial match: '{university}' shares keywords with {source} '{candidate}'"
                )

        return DimensionScore(0.0, f"No match: Program at '{university}', scholarship provider is '{provider}'")

    def _calc_field_match_with_evidence(
        self,
        scholarship: dict[str, Any],
        program_metadata: dict[str, Any],
    ) -> DimensionScore:
        """Calculate field match with evidence string."""
        scholarship_fields = self._criterion_values(scholarship, "field_of_study")

        if not scholarship_fields:
            return DimensionScore(1.0, "Scholarship open to all fields of study")

        program_field = program_metadata.get("field", "")
        normalized_program = self._normalize_text(program_field)

        if not normalized_program:
            return DimensionScore(0.5, f"Field not specified; scholarship targets: {', '.join(scholarship_fields)}")

        program_keywords = set(normalized_program.split())
        best_score = 0.0
        best_evidence = ""

        for field in scholarship_fields:
            normalized_field = self._normalize_text(field)
            if not normalized_field:
                continue

            if normalized_field == normalized_program:
                return DimensionScore(
                    1.0, f"Perfect field match: Program's '{program_field}' exactly matches '{field}'"
                )

            if normalized_field in normalized_program or normalized_program in normalized_field:
                if 0.9 > best_score:
                    best_score = 0.9
                    best_evidence = f"Strong field match: Program's '{program_field}' aligns with '{field}'"
                continue

            scholarship_keywords = set(normalized_field.split())
            overlap = scholarship_keywords & program_keywords
            union = scholarship_keywords | program_keywords
            if union:
                jaccard = len(overlap) / len(union)
                if jaccard > best_score:
                    best_score = jaccard
                    best_evidence = f"Keyword overlap: Program's '{program_field}' shares terms with '{field}'"

        if best_score > 0:
            return DimensionScore(best_score, best_evidence)

        return DimensionScore(0.0, f"No match: Program's '{program_field}' doesn't match scholarship fields")

    def _calc_degree_match_with_evidence(
        self,
        scholarship: dict[str, Any],
        program_metadata: dict[str, Any],
    ) -> DimensionScore:
        """Calculate degree match with evidence string."""
        scholarship_degrees = self._criterion_values(scholarship, "degree_level")

        if not scholarship_degrees:
            return DimensionScore(1.0, "Scholarship open to all degree levels")

        program_degree = program_metadata.get("degree_type", "")

        if not program_degree:
            return DimensionScore(0.5, f"Degree not specified; scholarship targets: {', '.join(scholarship_degrees)}")

        degree_map = {
            "bachelor": "bachelor",
            "undergraduate": "bachelor",
            "bsc": "bachelor",
            "ba": "bachelor",
            "master": "master",
            "masters": "master",
            "ms": "master",
            "msc": "master",
            "ma": "master",
            "phd": "phd",
            "postdoc": "phd",
            "postdoctoral": "phd",
            "doctoral": "phd",
            "doctorate": "phd",
        }

        program_key = self._normalize_text(program_degree)
        normalized_program = degree_map.get(program_degree.lower(), degree_map.get(program_key, program_key))
        normalized_scholarship = [
            degree_map.get(self._normalize_text(d), self._normalize_text(d)) for d in scholarship_degrees
        ]

        if normalized_program in normalized_scholarship:
            return DimensionScore(1.0, f"Perfect degree match: Program's '{program_degree}' matches eligible levels")

        return DimensionScore(
            0.0,
            f"Degree mismatch: Program's '{program_degree}' not in eligible levels: {', '.join(scholarship_degrees)}",
        )

    def _calc_geographic_match_with_evidence(
        self,
        scholarship: dict[str, Any],
        program_metadata: dict[str, Any],
    ) -> DimensionScore:
        """Calculate geographic match with evidence string."""
        scholarship_regions = self._criterion_values(scholarship, "region")
        scholarship_nationalities = self._criterion_values(scholarship, "nationality")

        if not scholarship_regions and not scholarship_nationalities:
            return DimensionScore(1.0, "Scholarship open to all regions/nationalities")

        program_country = program_metadata.get("country", "")

        if not program_country:
            restrictions = scholarship_regions + scholarship_nationalities
            return DimensionScore(0.5, f"Country not specified; scholarship targets: {', '.join(restrictions)}")

        for region in scholarship_regions:
            if entity_matches_region(program_country, region):
                countries = REGION_TO_COUNTRIES.get(region.lower())
                if countries:
                    return DimensionScore(
                        1.0, f"Regional match: Program country '{program_country}' is in eligible region '{region}'"
                    )
                return DimensionScore(1.0, f"Geographic match: Program country '{program_country}' matches '{region}'")

        normalized_country = self._normalize_text(program_country)
        for nationality in scholarship_nationalities:
            if normalized_country == self._normalize_text(nationality):
                return DimensionScore(1.0, f"Country match: Program country '{program_country}' is explicitly eligible")
            if entity_matches_region(program_country, nationality):
                return DimensionScore(
                    1.0, f"Country/region match: Program country '{program_country}' matches '{nationality}'"
                )

        restrictions = scholarship_regions + scholarship_nationalities
        return DimensionScore(
            0.0, f"Geographic restriction: Program country '{program_country}' not in eligible regions"
        )

    @staticmethod
    def _calc_university_match(scholarship: dict[str, Any], program_metadata: dict[str, Any]) -> float:
        """Direct university match with exact, substring, and acronym-aware fallbacks."""
        university = program_metadata.get("university_name", "")
        provider = scholarship.get("provider", "")
        candidates = [
            provider,
            scholarship.get("name", ""),
            scholarship.get("description", ""),
        ]

        if not university:
            return 0.0

        normalized_university = LinkingService._normalize_text(university)
        university_tokens = normalized_university.split()
        university_acronym = LinkingService._acronym(university_tokens)

        best_score = 0.0
        for candidate in candidates:
            normalized_candidate = LinkingService._normalize_text(candidate)
            if not normalized_candidate:
                continue

            if normalized_candidate == normalized_university:
                return 1.0

            if normalized_candidate in normalized_university or normalized_university in normalized_candidate:
                best_score = max(best_score, 1.0 if candidate == provider else 0.85)
                continue

            candidate_tokens = normalized_candidate.split()

            if (
                len(candidate_tokens) == 1
                and len(candidate_tokens[0]) <= 8
                and candidate_tokens[0] == university_acronym
            ):
                return 1.0

            if len(university_tokens) == 1 and len(university_tokens[0]) <= 8:
                candidate_acronym = LinkingService._acronym(candidate_tokens)
                if university_tokens[0] == candidate_acronym:
                    return 1.0

            overlap = set(candidate_tokens) & set(university_tokens)
            if len(overlap) >= 2:
                best_score = max(best_score, 0.9 if candidate == provider else 0.75)

        return best_score

    @staticmethod
    def _calc_field_match(scholarship: dict[str, Any], program_metadata: dict[str, Any]) -> float:
        """Field-of-study overlap (30% weight). Returns 0.0-1.0 based on keyword overlap."""
        scholarship_fields = LinkingService._criterion_values(scholarship, "field_of_study")

        if not scholarship_fields:
            return 1.0

        program_field = program_metadata.get("field", "")
        normalized_program = LinkingService._normalize_text(program_field)
        if not normalized_program:
            return 0.5

        best_score = 0.0
        program_keywords = set(normalized_program.split())
        for field in scholarship_fields:
            normalized_field = LinkingService._normalize_text(field)
            if not normalized_field:
                continue
            if normalized_field == normalized_program:
                return 1.0
            if normalized_field in normalized_program or normalized_program in normalized_field:
                best_score = max(best_score, 0.9)
                continue

            scholarship_keywords = set(normalized_field.split())
            overlap = scholarship_keywords & program_keywords
            union = scholarship_keywords | program_keywords
            if union:
                best_score = max(best_score, len(overlap) / len(union))

        return best_score

    @staticmethod
    def _calc_degree_match(scholarship: dict[str, Any], program_metadata: dict[str, Any]) -> float:
        """Degree-level match (15% weight). Returns 1.0 if exact match, 0.0 otherwise."""
        scholarship_degrees = LinkingService._criterion_values(scholarship, "degree_level")

        if not scholarship_degrees:
            return 1.0

        program_degree = program_metadata.get("degree_type", "")

        degree_map = {
            "bachelor": "bachelor",
            "undergraduate": "bachelor",
            "bsc": "bachelor",
            "ba": "bachelor",
            "master": "master",
            "masters": "master",
            "ms": "master",
            "msc": "master",
            "ma": "master",
            "master_coursework": "master",
            "master coursework": "master",
            "master_research": "master",
            "master research": "master",
            "phd": "phd",
            "postdoc": "phd",
            "postdoctoral": "phd",
            "doctoral": "phd",
            "doctorate": "phd",
        }

        program_key = LinkingService._normalize_text(program_degree)
        normalized_program = degree_map.get(program_degree.lower(), degree_map.get(program_key, program_key))
        normalized_scholarship = [
            degree_map.get(LinkingService._normalize_text(d), LinkingService._normalize_text(d))
            for d in scholarship_degrees
        ]

        if normalized_program in normalized_scholarship:
            return 1.0

        return 0.0

    @staticmethod
    def _calc_geographic_match(scholarship: dict[str, Any], program_metadata: dict[str, Any]) -> float:
        """Geographic/region match (5% weight). Returns 1.0 if region matches, 0.0 otherwise."""
        scholarship_regions = LinkingService._criterion_values(scholarship, "region")
        scholarship_nationalities = LinkingService._criterion_values(scholarship, "nationality")

        if not scholarship_regions and not scholarship_nationalities:
            return 1.0

        program_country = program_metadata.get("country", "")
        if not program_country:
            return 0.5

        for region in scholarship_regions:
            if entity_matches_region(program_country, region):
                return 1.0

        normalized_country = LinkingService._normalize_text(program_country)
        for nationality in scholarship_nationalities:
            if normalized_country == LinkingService._normalize_text(nationality):
                return 1.0
            if entity_matches_region(program_country, nationality):
                return 1.0

        return 0.0

    @staticmethod
    def _calculate_composite_confidence(
        university_score: float,
        field_score: float,
        degree_score: float,
        geographic_score: float,
    ) -> float:
        """Calculate weighted composite confidence in the range 0.0-1.0."""
        weights = settings.get_linking_weights()
        total_weight = sum(weights.values()) or 100
        confidence = (
            weights["university"] * university_score
            + weights["field"] * field_score
            + weights["degree"] * degree_score
            + weights["geographic"] * geographic_score
        ) / total_weight
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _determine_link_type(
        university_score: float, field_score: float, degree_score: float, geographic_score: float
    ) -> str:
        """Determine primary link type based on highest scoring dimension."""
        scores = {
            "university": university_score,
            "field": field_score,
            "degree": degree_score,
            "geographic": geographic_score,
        }
        return max(scores, key=scores.get)
