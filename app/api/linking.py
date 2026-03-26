"""Scholarship-program linking endpoints."""

from fastapi import APIRouter, Depends, Query

from app.middleware.service_auth import require_service_token
from app.models.linking import LinkRequest
from app.models.scholarship import ScholarshipResponse
from app.repositories.mysql_link_repo import LinkRepository
from app.repositories.mysql_scholarship_repo import ScholarshipRepository
from app.services.linking_service import LinkingService

router = APIRouter(prefix="/api/v1/scholarships", tags=["Linking"], dependencies=[Depends(require_service_token)])


@router.get("/by-program/{program_id}")
async def get_scholarships_by_program(
    program_id: str,
    min_confidence: float = Query(default=0.4, ge=0.0, le=1.0),
):
    """Get all scholarships linked to a specific program, sorted by confidence."""
    link_repo = LinkRepository()
    scholarship_repo = ScholarshipRepository()

    links = await link_repo.get_by_program_id(program_id=program_id, min_confidence=min_confidence)

    scholarships = []
    for link in links:
        scholarship = await scholarship_repo.get_by_id(link["scholarship_id"])
        if scholarship:
            scholarships.append(
                ScholarshipResponse(
                    id=scholarship["id"],
                    name=scholarship["name"],
                    provider=scholarship["provider"],
                    funding_amount=scholarship.get("funding_amount"),
                    currency=scholarship.get("currency", "USD"),
                    deadline=scholarship.get("deadline"),
                    description=scholarship.get("description"),
                    eligibility_criteria=scholarship.get("eligibility_criteria"),
                    application_requirements=scholarship.get("application_requirements"),
                    source_url=scholarship["source_url"],
                    crawled_at=scholarship.get("crawled_at"),
                    link_confidence=link["confidence_score"],
                    link_type=link["link_type"],
                )
            )

    return {"success": True, "data": scholarships}


@router.post("/link", response_model=dict)
async def create_link(request: LinkRequest):
    """Create or update a scholarship-program link."""
    service = LinkingService()
    link = await service.calculate_and_store_link(
        scholarship_id=request.scholarship_id,
        program_id=request.program_metadata.program_id,
        program_metadata=request.program_metadata.model_dump(),
    )

    if link is None:
        return {"success": True, "data": None, "message": "Confidence below threshold, link not stored"}

    return {"success": True, "data": link}
