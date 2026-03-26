"""Pydantic models for scholarship search requests and responses."""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StudentProfileFilter(BaseModel):
    """Student profile data for eligibility filtering."""

    gpa: Optional[float] = None
    gpa_scale: Optional[float] = Field(default=4.0)
    nationality: Optional[str] = None
    field_of_study: Optional[str] = None
    degree_type: Optional[str] = None
    language_test: Optional[str] = None


class ScholarshipSearchRequest(BaseModel):
    """Request body for POST /api/v1/scholarships/search."""

    student_profile: Optional[StudentProfileFilter] = None
    program_ids: list[str] = Field(default_factory=list)
    provider: Optional[str] = None
    max_results: int = Field(default=20, ge=1, le=100)
    page: int = Field(default=1, ge=1)


class ScholarshipResponse(BaseModel):
    """Single scholarship in search results."""

    id: str
    name: str
    provider: str
    funding_amount: Optional[float] = None
    currency: str = "USD"
    deadline: Optional[date] = None
    description: Optional[str] = None
    eligibility_criteria: Optional[dict[str, Any]] = None
    application_requirements: Optional[dict[str, Any]] = None
    source_url: str
    crawled_at: Optional[datetime] = None
    is_active: bool = True
    link_confidence: Optional[float] = Field(default=None, description="Confidence score for program link (0-1)")
    link_type: Optional[str] = Field(default=None, description="Primary link type to program")


class ScholarshipSearchResponse(BaseModel):
    """Response body for scholarship search."""

    success: bool = True
    data: list[ScholarshipResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class ScholarshipDetailResponse(BaseModel):
    """Full scholarship details including eligibility criteria."""

    success: bool = True
    data: Optional[ScholarshipResponse] = None
    eligibility_criteria_detailed: list[dict[str, Any]] = Field(default_factory=list)
