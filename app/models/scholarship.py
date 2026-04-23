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
    university: Optional[str] = Field(default=None, description="Current university/institution")
    current_institution: Optional[str] = Field(default=None, description="Alias for university")
    target_degree_level: Optional[str] = Field(
        default=None, description="Target degree level if different from current"
    )


class ProgramContext(BaseModel):
    """Program metadata for program-specific scholarship matching."""

    program_id: Optional[str] = None
    university_name: Optional[str] = None
    field: Optional[str] = None
    degree_type: Optional[str] = None
    country: Optional[str] = None


class ScholarshipSearchRequest(BaseModel):
    """Request body for POST /api/v1/scholarships/search."""

    student_profile: Optional[StudentProfileFilter] = None
    program_context: Optional[ProgramContext] = Field(default=None, description="Program metadata for matching")
    program_ids: list[str] = Field(default_factory=list)
    provider: Optional[str] = None
    max_results: int = Field(default=20, ge=1, le=100)
    page: int = Field(default=1, ge=1)
    include_explainability: bool = Field(default=True, description="Include match scores and reasoning in response")


class MatchScores(BaseModel):
    """4-dimension match scores for scholarship-profile alignment."""

    university_alignment: float = Field(ge=0.0, le=1.0, description="How well student's university matches scholarship")
    field_alignment: float = Field(ge=0.0, le=1.0, description="Field of study match score")
    degree_alignment: float = Field(ge=0.0, le=1.0, description="Degree level match score")
    geographic_alignment: float = Field(ge=0.0, le=1.0, description="Nationality/region match score")


class MatchEvidence(BaseModel):
    """Evidence strings explaining each dimension score."""

    university_alignment: str = Field(default="", description="Explanation for university score")
    field_alignment: str = Field(default="", description="Explanation for field score")
    degree_alignment: str = Field(default="", description="Explanation for degree score")
    geographic_alignment: str = Field(default="", description="Explanation for geographic score")


class EligibilityCheck(BaseModel):
    """Detailed eligibility check result."""

    is_eligible: bool = Field(description="Whether student meets all mandatory criteria")
    reasons_eligible: list[str] = Field(default_factory=list, description="Reasons why student qualifies")
    reasons_ineligible: list[str] = Field(default_factory=list, description="Reasons why student doesn't qualify")
    missing_info: list[str] = Field(default_factory=list, description="Missing info preventing full determination")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in eligibility determination")


class ScholarshipMatchBreakdown(BaseModel):
    """Complete match breakdown for a single scholarship."""

    scholarship_id: str
    scholarship_name: str
    provider: str
    amount: str
    deadline: Optional[str] = None
    composite_score: float = Field(ge=0.0, le=1.0)
    rank: Optional[int] = None
    decision: str = Field(description="recommend | consider | filter_out")
    match_scores: MatchScores
    match_evidence: MatchEvidence
    eligibility_check: EligibilityCheck


class EligibilitySummary(BaseModel):
    """Summary of eligibility across all evaluated scholarships."""

    total_scholarships_evaluated: int = 0
    fully_eligible: int = 0
    partially_eligible: int = 0
    ineligible: int = 0


class ScholarshipAgentReasoning(BaseModel):
    """Agent reasoning structure for explainability (matches SPA/PDA format)."""

    approach: str = Field(description="High-level matching strategy description")
    decision_factors: list[str] = Field(default_factory=list, description="Key factors in matching process")
    matching_breakdown: list[ScholarshipMatchBreakdown] = Field(
        default_factory=list, description="Top N scholarships with detailed scores"
    )
    filters_applied: list[str] = Field(default_factory=list, description="Criteria that filtered scholarships")
    eligibility_summary: EligibilitySummary = Field(default_factory=EligibilitySummary)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence in matches")
    model: Optional[str] = Field(default=None, description="LLM model used (if any)")
    provider: Optional[str] = Field(default=None, description="LLM provider (if any)")


class ScholarshipResponse(BaseModel):
    """Single scholarship in search results."""

    id: str
    name: str
    provider: str
    funding_amount: Optional[float] = None
    currency: Optional[str] = None
    deadline: Optional[date] = None
    description: Optional[str] = None
    eligibility_criteria: Optional[dict[str, Any]] = None
    application_requirements: Optional[dict[str, Any]] = None
    source_url: str
    crawled_at: Optional[datetime] = None
    is_active: bool = True
    link_confidence: Optional[float] = Field(default=None, description="Confidence score for program link (0-1)")
    link_type: Optional[str] = Field(default=None, description="Primary link type to program")
    match_confidence: Optional[float] = Field(
        default=None, description="Composite match score for student profile (0-1)"
    )
    match_scores: Optional[MatchScores] = Field(default=None, description="4-dimension match scores")
    match_evidence: Optional[MatchEvidence] = Field(default=None, description="Evidence for each dimension")
    eligibility_check: Optional[EligibilityCheck] = Field(default=None, description="Detailed eligibility result")


class ScholarshipSearchResponse(BaseModel):
    """Response body for scholarship search."""

    success: bool = True
    data: list[ScholarshipResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    agent_reasoning: Optional[ScholarshipAgentReasoning] = Field(
        default=None, description="Agent reasoning for explainability"
    )


class ScholarshipDetailResponse(BaseModel):
    """Full scholarship details including eligibility criteria."""

    success: bool = True
    data: Optional[ScholarshipResponse] = None
    eligibility_criteria_detailed: list[dict[str, Any]] = Field(default_factory=list)
    agent_reasoning: Optional[ScholarshipAgentReasoning] = Field(
        default=None, description="Agent reasoning if student_profile provided"
    )
