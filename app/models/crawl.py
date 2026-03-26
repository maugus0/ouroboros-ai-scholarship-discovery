"""Pydantic models for crawl job requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobType(str, Enum):
    BATCH = "batch"
    ON_DEMAND = "on_demand"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CrawlRequest(BaseModel):
    """Request body for POST /api/v1/scholarships/crawl."""

    job_type: JobType = JobType.ON_DEMAND
    target_url: Optional[str] = None
    target_source: Optional[str] = None


class CrawlJobResponse(BaseModel):
    """Single crawl job status."""

    id: str
    job_type: str
    status: str
    target_url: Optional[str] = None
    target_source: Optional[str] = None
    scholarships_crawled: int = 0
    scholarships_updated: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class CrawlTriggerResponse(BaseModel):
    """Response for crawl trigger endpoint."""

    success: bool = True
    data: Optional[CrawlJobResponse] = None
    message: str = "Crawl job created"


class CrawlStatusResponse(BaseModel):
    """Response for crawl status endpoint."""

    success: bool = True
    data: Optional[CrawlJobResponse] = None


class CrawlListResponse(BaseModel):
    """Response for listing crawl jobs."""

    success: bool = True
    data: list[CrawlJobResponse] = Field(default_factory=list)
    total: int = 0
