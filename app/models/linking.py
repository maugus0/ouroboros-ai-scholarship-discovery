"""Pydantic models for scholarship-program linking."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ProgramMetadata(BaseModel):
    """Program metadata passed by the Orchestrator for linking."""

    program_id: str
    university_name: str
    field: str
    degree_type: str
    country: Optional[str] = None


class LinkRequest(BaseModel):
    """Request to create/update a scholarship-program link."""

    scholarship_id: str
    program_metadata: ProgramMetadata


class LinkResponse(BaseModel):
    """Response for a scholarship-program link."""

    id: str
    scholarship_id: str
    program_id: str
    link_type: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    match_metadata: Optional[dict[str, Any]] = None


class ConfidenceBreakdown(BaseModel):
    """Detailed breakdown of the 4-dimension confidence score."""

    university_score: float = 0.0
    field_score: float = 0.0
    degree_score: float = 0.0
    geographic_score: float = 0.0
    total_confidence: float = 0.0


class LLMExtractionResult(BaseModel):
    """Result from LLM-based scholarship extraction."""

    extracted_data: dict = Field(default_factory=dict)
    provider: str = ""
    model: str = ""
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
