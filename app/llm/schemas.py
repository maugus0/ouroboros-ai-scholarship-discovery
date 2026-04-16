"""Pydantic schemas for LLM output validation."""

from typing import Optional

from pydantic import BaseModel, Field


class ExtractedScholarshipData(BaseModel):
    """Structured scholarship data extracted from HTML by the LLM."""

    name: Optional[str] = None
    provider: Optional[str] = None
    funding_amount: Optional[float] = None
    currency: Optional[str] = None
    deadline: Optional[str] = None
    description: Optional[str] = None
    eligibility_criteria: Optional[dict] = None
    application_requirements: Optional[dict] = None


class ParsedEligibilityCriterion(BaseModel):
    """A single parsed eligibility criterion."""

    type: str
    value: str
    is_mandatory: bool = True


class ParsedEligibilityCriteria(BaseModel):
    """Collection of parsed eligibility criteria from LLM."""

    criteria: list[ParsedEligibilityCriterion] = Field(default_factory=list)


class FieldClassification(BaseModel):
    """Field classification result from LLM."""

    field: str
    field_category: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
