"""Scholarship search and retrieval endpoints with ReAct explainability."""

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from app.core.logging import get_logger
from app.middleware.service_auth import require_service_token
from app.models.scholarship import (
    EligibilityCheck,
    EligibilitySummary,
    MatchEvidence,
    MatchScores,
    ScholarshipAgentReasoning,
    ScholarshipDetailResponse,
    ScholarshipMatchBreakdown,
    ScholarshipResponse,
    ScholarshipSearchRequest,
    ScholarshipSearchResponse,
)
from app.services.scholarship_service import ScholarshipService
from app.utils.exceptions import NotFoundError

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/scholarships", tags=["Scholarships"], dependencies=[Depends(require_service_token)])


def _json_field(value: Any) -> dict[str, Any] | None:
    """Decode MySQL JSON/TEXT values before returning API responses."""
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _to_scholarship_response(scholarship: dict[str, Any], include_explainability: bool = True) -> ScholarshipResponse:
    """Map a database row into an API response model with optional explainability."""
    response = ScholarshipResponse(
        id=scholarship["id"],
        name=scholarship["name"],
        provider=scholarship["provider"],
        funding_amount=scholarship.get("funding_amount"),
        currency=scholarship.get("currency"),
        deadline=scholarship.get("deadline"),
        description=scholarship.get("description"),
        eligibility_criteria=_json_field(scholarship.get("eligibility_criteria")),
        application_requirements=_json_field(scholarship.get("application_requirements")),
        source_url=scholarship.get("source_url", ""),
        crawled_at=scholarship.get("crawled_at"),
        is_active=scholarship.get("is_active", True),
        link_confidence=scholarship.get("link_confidence"),
        link_type=scholarship.get("link_type"),
    )

    if include_explainability:
        if scholarship.get("match_confidence") is not None:
            response.match_confidence = scholarship["match_confidence"]

        if scholarship.get("match_scores"):
            scores = scholarship["match_scores"]
            response.match_scores = MatchScores(
                university_alignment=scores.get("university_alignment", 0.0),
                field_alignment=scores.get("field_alignment", 0.0),
                degree_alignment=scores.get("degree_alignment", 0.0),
                geographic_alignment=scores.get("geographic_alignment", 0.0),
            )

        if scholarship.get("match_evidence"):
            evidence = scholarship["match_evidence"]
            response.match_evidence = MatchEvidence(
                university_alignment=evidence.get("university_alignment", ""),
                field_alignment=evidence.get("field_alignment", ""),
                degree_alignment=evidence.get("degree_alignment", ""),
                geographic_alignment=evidence.get("geographic_alignment", ""),
            )

        if scholarship.get("eligibility_check"):
            check = scholarship["eligibility_check"]
            response.eligibility_check = EligibilityCheck(
                is_eligible=check.get("is_eligible", True),
                reasons_eligible=check.get("reasons_eligible", []),
                reasons_ineligible=check.get("reasons_ineligible", []),
                missing_info=check.get("missing_info", []),
                confidence=check.get("confidence", 1.0),
            )

    return response


def _to_agent_reasoning(reasoning: Optional[dict[str, Any]]) -> Optional[ScholarshipAgentReasoning]:
    """Convert agent reasoning dict to Pydantic model."""
    if not reasoning:
        return None

    matching_breakdown = []
    for match in reasoning.get("matching_breakdown", []):
        scores = match.get("match_scores", {})
        evidence = match.get("match_evidence", {})
        eligibility = match.get("eligibility_check", {})

        breakdown = ScholarshipMatchBreakdown(
            scholarship_id=match.get("scholarship_id", ""),
            scholarship_name=match.get("scholarship_name", ""),
            provider=match.get("provider", ""),
            amount=match.get("amount", ""),
            deadline=match.get("deadline"),
            composite_score=match.get("composite_score", 0.0),
            rank=match.get("rank"),
            decision=match.get("decision", "consider"),
            match_scores=MatchScores(
                university_alignment=scores.get("university_alignment", 0.0),
                field_alignment=scores.get("field_alignment", 0.0),
                degree_alignment=scores.get("degree_alignment", 0.0),
                geographic_alignment=scores.get("geographic_alignment", 0.0),
            ),
            match_evidence=MatchEvidence(
                university_alignment=evidence.get("university_alignment", ""),
                field_alignment=evidence.get("field_alignment", ""),
                degree_alignment=evidence.get("degree_alignment", ""),
                geographic_alignment=evidence.get("geographic_alignment", ""),
            ),
            eligibility_check=EligibilityCheck(
                is_eligible=eligibility.get("is_eligible", True),
                reasons_eligible=eligibility.get("reasons_eligible", []),
                reasons_ineligible=eligibility.get("reasons_ineligible", []),
                missing_info=eligibility.get("missing_info", []),
                confidence=eligibility.get("confidence", 1.0),
            ),
        )
        matching_breakdown.append(breakdown)

    summary = reasoning.get("eligibility_summary", {})
    eligibility_summary = EligibilitySummary(
        total_scholarships_evaluated=summary.get("total_scholarships_evaluated", 0),
        fully_eligible=summary.get("fully_eligible", 0),
        partially_eligible=summary.get("partially_eligible", 0),
        ineligible=summary.get("ineligible", 0),
    )

    return ScholarshipAgentReasoning(
        approach=reasoning.get("approach", ""),
        decision_factors=reasoning.get("decision_factors", []),
        matching_breakdown=matching_breakdown,
        filters_applied=reasoning.get("filters_applied", []),
        eligibility_summary=eligibility_summary,
        confidence=reasoning.get("confidence", 0.0),
        model=reasoning.get("model"),
        provider=reasoning.get("provider"),
    )


@router.post("/search", response_model=ScholarshipSearchResponse)
async def search_scholarships(request: ScholarshipSearchRequest):
    """Search and filter scholarships with full ReAct explainability.

    When `student_profile` is provided:
    - Scholarships are matched using 4-dimension scoring (university, field, degree, geographic)
    - Eligibility is checked against all mandatory criteria
    - Results are ranked by composite match score
    - Full `agent_reasoning` is included in response

    When `include_explainability=false`:
    - Match scores and evidence are omitted from individual scholarships
    - Faster response for bulk retrieval
    """
    service = ScholarshipService()

    student_profile_dict = request.student_profile.model_dump() if request.student_profile else None
    program_context_dict = request.program_context.model_dump() if request.program_context else None

    result = await service.search_with_explainability(
        student_profile=student_profile_dict,
        program_context=program_context_dict,
        provider=request.provider,
        program_ids=request.program_ids if request.program_ids else None,
        limit=request.max_results,
        page=request.page,
    )

    scholarships = result.get("scholarships", [])
    data = [_to_scholarship_response(s, include_explainability=request.include_explainability) for s in scholarships]

    agent_reasoning = None
    if request.include_explainability and result.get("agent_reasoning"):
        agent_reasoning = _to_agent_reasoning(result["agent_reasoning"])

    return ScholarshipSearchResponse(
        success=True,
        data=data,
        total=result.get("total", 0),
        page=result.get("page", 1),
        page_size=result.get("page_size", request.max_results),
        agent_reasoning=agent_reasoning,
    )


@router.get("/{scholarship_id}", response_model=ScholarshipDetailResponse)
async def get_scholarship(
    scholarship_id: str,
    gpa: Optional[float] = Query(default=None, description="Student GPA for eligibility check"),
    gpa_scale: Optional[float] = Query(default=4.0, description="GPA scale (default 4.0)"),
    nationality: Optional[str] = Query(default=None, description="Student nationality"),
    field_of_study: Optional[str] = Query(default=None, description="Student field of study"),
    degree_type: Optional[str] = Query(default=None, description="Student degree type (bachelor/master/phd)"),
    language_test: Optional[str] = Query(default=None, description="Language test score (e.g., 'IELTS 7.5')"),
    university: Optional[str] = Query(default=None, description="Student current university"),
):
    """Get full scholarship details with optional eligibility check.

    If any student profile fields are provided via query params, eligibility checking
    and match scoring will be performed, with results included in `agent_reasoning`.
    """
    service = ScholarshipService()

    has_profile = any([gpa, nationality, field_of_study, degree_type, language_test, university])

    student_profile = None
    if has_profile:
        student_profile = {
            "gpa": gpa,
            "gpa_scale": gpa_scale,
            "nationality": nationality,
            "field_of_study": field_of_study,
            "degree_type": degree_type,
            "language_test": language_test,
            "university": university,
        }
        student_profile = {k: v for k, v in student_profile.items() if v is not None}

    result = await service.get_scholarship_detail_with_explainability(
        scholarship_id=scholarship_id,
        student_profile=student_profile,
    )

    if not result:
        raise NotFoundError("Scholarship")

    scholarship = result.get("scholarship", {})
    criteria = result.get("eligibility_criteria_detailed", [])
    reasoning = result.get("agent_reasoning")

    response_data = _to_scholarship_response(scholarship, include_explainability=has_profile)
    agent_reasoning = _to_agent_reasoning(reasoning) if reasoning else None

    return ScholarshipDetailResponse(
        success=True,
        data=response_data,
        eligibility_criteria_detailed=criteria,
        agent_reasoning=agent_reasoning,
    )
