"""Scholarship search, filter, and storage orchestration with ReAct explainability."""

from typing import Any, Optional

from app.agents.scholarship_matching_engine import apply_react_matching_pattern
from app.config import settings
from app.core.logging import get_logger
from app.repositories.mysql_eligibility_criteria_repo import EligibilityCriteriaRepository
from app.repositories.mysql_link_repo import LinkRepository
from app.repositories.mysql_scholarship_repo import ScholarshipRepository

logger = get_logger(__name__)


class ScholarshipService:
    """Business logic for scholarship search and discovery with explainability."""

    def __init__(self):
        self.scholarship_repo = ScholarshipRepository()
        self.link_repo = LinkRepository()
        self.criteria_repo = EligibilityCriteriaRepository()

    async def search(
        self,
        provider: str | None = None,
        program_ids: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search scholarships with optional filters (legacy method without explainability).

        If ``program_ids`` is provided, only scholarships linked to those programs (via
        ``scholarship_program_links``) are included. Pagination applies after that filter.
        """
        scholarship_ids: list[str] | None = None
        if program_ids:
            scholarship_ids = await self.link_repo.get_scholarship_ids_for_programs(program_ids)

        scholarships = await self.scholarship_repo.search_scholarships(
            provider=provider,
            scholarship_ids=scholarship_ids,
            limit=limit,
            offset=offset,
        )

        total = await self.scholarship_repo.count_scholarships(
            provider=provider,
            scholarship_ids=scholarship_ids,
        )

        return {
            "scholarships": scholarships,
            "total": total,
        }

    async def search_with_explainability(
        self,
        student_profile: Optional[dict[str, Any]] = None,
        program_context: Optional[dict[str, Any]] = None,
        provider: str | None = None,
        program_ids: list[str] | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> dict[str, Any]:
        """Search scholarships with full ReAct explainability.

        Args:
            student_profile: Student profile for matching and eligibility
            program_context: Program metadata for program-specific matching
            provider: Filter by scholarship provider
            program_ids: Filter to scholarships linked to these programs
            limit: Max results per page
            page: Page number (1-indexed)

        Returns:
            Dict with scholarships, total, page, page_size, and agent_reasoning
        """
        # Only filter by program_ids if no provider is specified
        # When provider is specified, we search by provider directly
        # program_ids filter requires scholarship_program_links which may not exist
        scholarship_ids: list[str] | None = None
        if program_ids and not provider:
            scholarship_ids = await self.link_repo.get_scholarship_ids_for_programs(program_ids)
            # If no scholarships are linked to the given programs, return empty result early
            if not scholarship_ids:
                return {
                    "scholarships": [],
                    "total": 0,
                    "page": page,
                    "page_size": limit,
                    "agent_reasoning": None,
                }

        all_scholarships = await self.scholarship_repo.search_scholarships(
            provider=provider,
            scholarship_ids=scholarship_ids,
            limit=1000,
            offset=0,
        )

        total_before_matching = len(all_scholarships)

        if not student_profile:
            offset = (page - 1) * limit
            paginated = all_scholarships[offset : offset + limit]

            total = await self.scholarship_repo.count_scholarships(
                provider=provider,
                scholarship_ids=scholarship_ids,
            )

            # Always provide agent reasoning even without profile matching
            agent_reasoning = {
                "approach": "Retrieved scholarships without profile-based matching.",
                "confidence": 0.70,
                "decision_factors": [
                    f"Total scholarships found: {total}",
                    f"Provider filter: {provider or 'None'}",
                    "No student profile provided for eligibility matching",
                    "Results ordered by deadline",
                ],
                "eligibility_summary": {
                    "total_scholarships_evaluated": 0,
                    "fully_eligible": 0,
                    "partially_eligible": 0,
                    "ineligible": 0,
                    "note": "Profile-based eligibility not evaluated (no profile provided)",
                },
            }

            return {
                "scholarships": paginated,
                "total": total,
                "page": page,
                "page_size": limit,
                "agent_reasoning": agent_reasoning,
            }

        criteria_by_scholarship = await self._load_criteria_for_scholarships(all_scholarships)

        react_result = apply_react_matching_pattern(
            scholarships=all_scholarships,
            student_profile=student_profile,
            program_context=program_context,
            criteria_by_scholarship=criteria_by_scholarship,
        )

        ranked = react_result.get("ranked_scholarships", [])

        offset = (page - 1) * limit
        paginated_matches = ranked[offset : offset + limit]

        enriched_scholarships = []
        for match in paginated_matches:
            original = next(
                (s for s in all_scholarships if s.get("id") == match["scholarship_id"]),
                None,
            )
            if original:
                enriched = dict(original)
                enriched["match_confidence"] = match["composite_score"]
                enriched["match_scores"] = match["match_scores"]
                enriched["match_evidence"] = match["match_evidence"]
                enriched["eligibility_check"] = match["eligibility_check"]
                enriched_scholarships.append(enriched)

        agent_reasoning = self._build_agent_reasoning(
            react_result=react_result,
            student_profile=student_profile,
            total_evaluated=total_before_matching,
            limit=limit,
        )

        return {
            "scholarships": enriched_scholarships,
            "total": len(ranked),
            "page": page,
            "page_size": limit,
            "agent_reasoning": agent_reasoning,
        }

    async def get_scholarship_detail_with_explainability(
        self,
        scholarship_id: str,
        student_profile: Optional[dict[str, Any]] = None,
        program_context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any] | None:
        """Return full scholarship details with optional explainability.

        Args:
            scholarship_id: Scholarship ID
            student_profile: Optional student profile for matching
            program_context: Optional program context for matching

        Returns:
            Scholarship details with optional match scores and reasoning
        """
        scholarship = await self.scholarship_repo.get_by_id(scholarship_id)
        if not scholarship:
            return None

        criteria = await self.criteria_repo.get_by_scholarship_id(scholarship_id)

        result = {
            "scholarship": scholarship,
            "eligibility_criteria_detailed": criteria,
            "agent_reasoning": None,
        }

        if student_profile:
            criteria_map = {scholarship_id: criteria} if criteria else {}

            react_result = apply_react_matching_pattern(
                scholarships=[scholarship],
                student_profile=student_profile,
                program_context=program_context,
                criteria_by_scholarship=criteria_map,
            )

            ranked = react_result.get("ranked_scholarships", [])
            if ranked:
                match = ranked[0]
                result["scholarship"]["match_confidence"] = match["composite_score"]
                result["scholarship"]["match_scores"] = match["match_scores"]
                result["scholarship"]["match_evidence"] = match["match_evidence"]
                result["scholarship"]["eligibility_check"] = match["eligibility_check"]

            result["agent_reasoning"] = self._build_agent_reasoning(
                react_result=react_result,
                student_profile=student_profile,
                total_evaluated=1,
                limit=1,
            )

        return result

    async def get_scholarship_detail(self, scholarship_id: str) -> dict[str, Any] | None:
        """Return full scholarship details (legacy method)."""
        scholarship = await self.scholarship_repo.get_by_id(scholarship_id)
        if not scholarship:
            return None
        return scholarship

    async def get_stale_scholarships(self) -> list[dict[str, Any]]:
        """Return scholarships not crawled within the staleness threshold."""
        return await self.scholarship_repo.get_stale_scholarships(settings.SCHOLARSHIP_STALENESS_DAYS)

    async def store_crawled_scholarship(self, data: dict[str, Any]) -> str:
        """Store or update a crawled scholarship."""
        existing = None
        if data.get("source_url"):
            existing = await self.scholarship_repo.get_by_source_url(data["source_url"])

        if existing:
            await self.scholarship_repo.update_scholarship(existing["id"], data)
            logger.info("scholarship_updated_from_crawl", scholarship_id=existing["id"])
            return existing["id"]

        scholarship_id = await self.scholarship_repo.create_scholarship(data)
        logger.info("scholarship_created_from_crawl", scholarship_id=scholarship_id)
        return scholarship_id

    async def get_all_active(self) -> list[dict[str, Any]]:
        """Return all active scholarships."""
        return await self.scholarship_repo.get_all_active()

    async def _load_criteria_for_scholarships(
        self,
        scholarships: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Load eligibility criteria for all scholarships in batch."""
        result: dict[str, list[dict[str, Any]]] = {}
        for scholarship in scholarships:
            sid = scholarship.get("id")
            if sid:
                criteria = await self.criteria_repo.get_by_scholarship_id(sid)
                if criteria:
                    result[sid] = criteria
        return result

    def _build_agent_reasoning(
        self,
        react_result: dict[str, Any],
        student_profile: dict[str, Any],
        total_evaluated: int,
        limit: int,
    ) -> dict[str, Any]:
        """Build agent_reasoning structure matching SPA/PDA format."""
        eligibility_summary = react_result.get("eligibility_summary", {})
        filters_applied = react_result.get("filters_applied", [])
        ranked = react_result.get("ranked_scholarships", [])
        confidence_map = react_result.get("confidence_map", {})

        avg_confidence = sum(confidence_map.values()) / len(confidence_map) if confidence_map else 0.0

        profile_summary = self._summarize_profile(student_profile)

        approach = (
            f"Evaluated {total_evaluated} scholarships against student profile ({profile_summary}), "
            f"ranked by 4-dimension weighted scoring (university: {settings.LINKING_WEIGHT_UNIVERSITY}%, "
            f"field: {settings.LINKING_WEIGHT_FIELD}%, degree: {settings.LINKING_WEIGHT_DEGREE}%, "
            f"geographic: {settings.LINKING_WEIGHT_GEOGRAPHIC}%), filtered to eligible matches."
        )

        decision_factors = [
            f"Student profile: {profile_summary}",
            f"Found {total_evaluated} active scholarships",
        ]
        decision_factors.extend(filters_applied)

        if ranked:
            top_scores = [r["composite_score"] for r in ranked[:5]]
            if top_scores:
                decision_factors.append(
                    f"Top {len(top_scores)} scholarships have composite scores: {', '.join(f'{s:.2f}' for s in top_scores)}"
                )

        matching_breakdown = ranked[: min(10, limit)]

        return {
            "approach": approach,
            "decision_factors": decision_factors,
            "matching_breakdown": matching_breakdown,
            "filters_applied": filters_applied,
            "eligibility_summary": eligibility_summary,
            "confidence": round(avg_confidence, 3),
            "model": None,
            "provider": None,
        }

    @staticmethod
    def _summarize_profile(profile: dict[str, Any]) -> str:
        """Create human-readable profile summary."""
        parts = []
        degree = profile.get("degree_type") or profile.get("target_degree_level")
        if degree:
            parts.append(f"{degree}'s")
        if profile.get("field_of_study"):
            parts.append(f"in {profile['field_of_study']}")
        university = profile.get("university") or profile.get("current_institution")
        if university:
            parts.append(f"at {university}")
        if profile.get("gpa"):
            parts.append(f"GPA {profile['gpa']}")
        if profile.get("nationality"):
            parts.append(f"({profile['nationality']} national)")
        return " ".join(parts) if parts else "incomplete profile"
