"""4-Dimension Scholarship-Program Linking Service.

Calculates confidence scores across university, field, degree, and geographic dimensions.
"""

from typing import Any, Optional

from app.config import settings
from app.core.logging import get_logger
from app.repositories.mysql_link_repo import LinkRepository
from app.repositories.mysql_scholarship_repo import ScholarshipRepository

logger = get_logger(__name__)

REGION_MAP = {
    "asia": ["china", "india", "japan", "south korea", "singapore", "thailand", "vietnam"],
    "europe": ["uk", "united kingdom", "germany", "france", "netherlands", "sweden", "switzerland"],
    "north america": ["usa", "united states", "canada", "mexico"],
    "south america": ["brazil", "argentina", "chile", "colombia"],
    "oceania": ["australia", "new zealand"],
    "africa": ["south africa", "nigeria", "kenya", "egypt"],
}


class LinkingService:
    """Calculate and store 4-dimension scholarship-program links."""

    def __init__(self):
        self.link_repo = LinkRepository()
        self.scholarship_repo = ScholarshipRepository()

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

        weights = settings.get_linking_weights()
        confidence = (
            weights["university"] / 100.0 * university_score
            + weights["field"] / 100.0 * field_score
            + weights["degree"] / 100.0 * degree_score
            + weights["geographic"] / 100.0 * geographic_score
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

    @staticmethod
    def _calc_university_match(scholarship: dict[str, Any], program_metadata: dict[str, Any]) -> float:
        """Direct university match (50% weight). Returns 1.0 if same university, 0.0 otherwise."""
        provider = scholarship.get("provider", "").lower()
        university = program_metadata.get("university_name", "").lower()

        if not provider or not university:
            return 0.0

        if provider == university:
            return 1.0

        if provider in university or university in provider:
            return 1.0

        return 0.0

    @staticmethod
    def _calc_field_match(scholarship: dict[str, Any], program_metadata: dict[str, Any]) -> float:
        """Field-of-study overlap (30% weight). Returns 0.0-1.0 based on keyword overlap."""
        eligibility = scholarship.get("eligibility_criteria") or {}
        if isinstance(eligibility, str):
            return 0.5

        scholarship_fields = eligibility.get("field_of_study", [])

        if not scholarship_fields:
            return 1.0

        program_field = program_metadata.get("field", "")

        if isinstance(scholarship_fields, list):
            if program_field in scholarship_fields:
                return 1.0

            scholarship_keywords = set(" ".join(scholarship_fields).lower().split())
        else:
            scholarship_keywords = set(str(scholarship_fields).lower().split())

        program_keywords = set(program_field.lower().split())

        overlap = scholarship_keywords & program_keywords
        union = scholarship_keywords | program_keywords

        if not union:
            return 0.0

        return len(overlap) / len(union)

    @staticmethod
    def _calc_degree_match(scholarship: dict[str, Any], program_metadata: dict[str, Any]) -> float:
        """Degree-level match (15% weight). Returns 1.0 if exact match, 0.0 otherwise."""
        eligibility = scholarship.get("eligibility_criteria") or {}
        if isinstance(eligibility, str):
            return 0.5

        scholarship_degrees = eligibility.get("degree_level", [])

        if not scholarship_degrees:
            return 1.0

        program_degree = program_metadata.get("degree_type", "")

        degree_map = {
            "bachelor": "bachelor", "undergraduate": "bachelor", "bsc": "bachelor", "ba": "bachelor",
            "master": "master", "ms": "master", "msc": "master", "ma": "master",
            "master_coursework": "master", "master_research": "master",
            "phd": "phd", "doctoral": "phd", "doctorate": "phd",
        }

        normalized_program = degree_map.get(program_degree.lower(), program_degree.lower())
        normalized_scholarship = [degree_map.get(d.lower(), d.lower()) for d in scholarship_degrees]

        if normalized_program in normalized_scholarship:
            return 1.0

        return 0.0

    @staticmethod
    def _calc_geographic_match(scholarship: dict[str, Any], program_metadata: dict[str, Any]) -> float:
        """Geographic/region match (5% weight). Returns 1.0 if region matches, 0.0 otherwise."""
        eligibility = scholarship.get("eligibility_criteria") or {}
        if isinstance(eligibility, str):
            return 0.5

        scholarship_regions = eligibility.get("region", [])

        if not scholarship_regions:
            return 1.0

        program_country = program_metadata.get("country", "")
        if not program_country:
            return 0.5

        for region in scholarship_regions:
            region_lower = region.lower()
            country_lower = program_country.lower()

            if region_lower in REGION_MAP:
                if country_lower in REGION_MAP[region_lower]:
                    return 1.0
            elif region_lower == country_lower:
                return 1.0

        return 0.0

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
