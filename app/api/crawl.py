"""Crawl trigger and status endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends

from app.middleware.service_auth import require_service_token
from app.models.crawl import (
    CrawlJobResponse,
    CrawlListResponse,
    CrawlRequest,
    CrawlStatusResponse,
    CrawlTriggerResponse,
)
from app.services.crawl_service import CrawlService
from app.utils.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/api/v1/scholarships", tags=["Crawl"], dependencies=[Depends(require_service_token)])


@router.post("/crawl", response_model=CrawlTriggerResponse)
async def trigger_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """Trigger a new crawl job (on-demand or batch)."""
    if request.job_type == "on_demand" and not request.target_url and not request.target_source:
        raise ValidationError("On-demand crawl requires target_url or target_source")

    service = CrawlService()
    job_id = await service.create_job(
        {
            "job_type": request.job_type.value,
            "target_url": request.target_url,
            "target_source": request.target_source,
        }
    )

    if request.target_url:
        background_tasks.add_task(service.execute_on_demand_crawl, job_id, request.target_url)
    elif request.target_source:
        background_tasks.add_task(service.execute_source_crawl, job_id, request.target_source)

    job = await service.get_job_status(job_id)
    job_response = CrawlJobResponse(**job) if job else CrawlJobResponse(id=job_id, job_type=request.job_type, status="pending")

    return CrawlTriggerResponse(success=True, data=job_response, message="Crawl job created")


@router.get("/crawl/{job_id}", response_model=CrawlStatusResponse)
async def get_crawl_status(job_id: str):
    """Get the current status of a crawl job."""
    service = CrawlService()
    job = await service.get_job_status(job_id)

    if not job:
        raise NotFoundError("Crawl job")

    return CrawlStatusResponse(success=True, data=CrawlJobResponse(**job))


@router.get("/crawl", response_model=CrawlListResponse)
async def list_crawl_jobs(limit: int = 20, offset: int = 0, status: str | None = None):
    """List crawl jobs with optional status filter."""
    service = CrawlService()
    jobs = await service.list_jobs(limit=limit, offset=offset, status=status)

    return CrawlListResponse(
        success=True,
        data=[CrawlJobResponse(**j) for j in jobs],
        total=len(jobs),
    )
