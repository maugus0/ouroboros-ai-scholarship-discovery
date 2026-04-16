"""Scholarship-program linking endpoints.

``program_id`` values are orchestrator-supplied opaque IDs (not a foreign key to Program Discovery DB).
"""

from fastapi import APIRouter, Depends, Query

from app.middleware.service_auth import require_service_token
from app.models.linking import LinkRequest
from app.models.scholarship import ScholarshipSearchResponse
from app.api.scholarships import _to_scholarship_response
from app.config import settings
from app.repositories.mysql_link_repo import LinkRepository
from app.repositories.mysql_scholarship_repo import ScholarshipRepository
from app.services.linking_service import LinkingService

router = APIRouter(prefix="/api/v1/scholarships", tags=["Linking"], dependencies=[Depends(require_service_token)])


@router.get("/by-program/{program_id}")
async def get_scholarships_by_program(
    program_id: str,
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0, description="Minimum link confidence"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> ScholarshipSearchResponse:
    """Get scholarships linked to a specific program, sorted by link confidence."""
    link_repo = LinkRepository()
    scholarship_repo = ScholarshipRepository()
    threshold = settings.MIN_LINK_CONFIDENCE_SCORE if min_confidence is None else min_confidence
    links = await link_repo.get_by_program_id(program_id=program_id, min_confidence=threshold)

    start = (page - 1) * limit
    page_links = links[start : start + limit]
    scholarships = []
    for link in page_links:
        scholarship = await scholarship_repo.get_by_id(link["scholarship_id"])
        if not scholarship:
            continue
        scholarship["link_confidence"] = link.get("confidence_score")
        scholarship["link_type"] = link.get("link_type")
        scholarships.append(scholarship)

    data = [_to_scholarship_response(scholarship) for scholarship in scholarships]

    return ScholarshipSearchResponse(
        success=True,
        data=data,
        total=len(links),
        page=page,
        page_size=limit,
    )


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
