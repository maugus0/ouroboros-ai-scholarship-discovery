"""Scholarship search and retrieval endpoints."""

import json
from typing import Any

from fastapi import APIRouter, Depends

from app.middleware.service_auth import require_service_token
from app.models.scholarship import (
    ScholarshipDetailResponse,
    ScholarshipResponse,
    ScholarshipSearchRequest,
    ScholarshipSearchResponse,
)
from app.repositories.mysql_eligibility_criteria_repo import EligibilityCriteriaRepository
from app.services.eligibility_filter_service import EligibilityFilterService
from app.services.scholarship_service import ScholarshipService
from app.utils.exceptions import NotFoundError

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


def _to_scholarship_response(scholarship: dict[str, Any]) -> ScholarshipResponse:
    """Map a database row into an API response model."""
    return ScholarshipResponse(
        id=scholarship["id"],
        name=scholarship["name"],
        provider=scholarship["provider"],
        funding_amount=scholarship.get("funding_amount"),
        currency=scholarship.get("currency"),
        deadline=scholarship.get("deadline"),
        description=scholarship.get("description"),
        eligibility_criteria=_json_field(scholarship.get("eligibility_criteria")),
        application_requirements=_json_field(scholarship.get("application_requirements")),
        source_url=scholarship["source_url"],
        crawled_at=scholarship.get("crawled_at"),
        is_active=scholarship.get("is_active", True),
        link_confidence=scholarship.get("link_confidence"),
        link_type=scholarship.get("link_type"),
    )


@router.post("/search", response_model=ScholarshipSearchResponse)
async def search_scholarships(request: ScholarshipSearchRequest):
    """Search and filter scholarships based on student profile."""
    service = ScholarshipService()
    result = await service.search(
        provider=request.provider,
        program_ids=request.program_ids if request.program_ids else None,
        limit=request.max_results,
        offset=(request.page - 1) * request.max_results,
    )

    scholarships = result["scholarships"]

    if request.student_profile:
        filter_service = EligibilityFilterService()
        scholarships = await filter_service.filter_eligible(
            student_profile=request.student_profile.model_dump(),
            scholarships=scholarships,
        )

    data = [_to_scholarship_response(s) for s in scholarships]

    return ScholarshipSearchResponse(
        success=True,
        data=data,
        total=result["total"],
        page=request.page,
        page_size=request.max_results,
    )


@router.get("/{scholarship_id}", response_model=ScholarshipDetailResponse)
async def get_scholarship(scholarship_id: str):
    """Get full scholarship details including eligibility criteria."""
    service = ScholarshipService()
    scholarship = await service.get_scholarship_detail(scholarship_id)

    if not scholarship:
        raise NotFoundError("Scholarship")

    criteria_repo = EligibilityCriteriaRepository()
    criteria = await criteria_repo.get_by_scholarship_id(scholarship_id)

    response_data = _to_scholarship_response(scholarship)

    return ScholarshipDetailResponse(
        success=True,
        data=response_data,
        eligibility_criteria_detailed=criteria,
    )
