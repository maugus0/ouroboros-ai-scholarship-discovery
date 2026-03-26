"""Pydantic models for eligibility criteria."""

from typing import Optional

from pydantic import BaseModel, Field


class EligibilityCriterion(BaseModel):
    """A single eligibility criterion entry."""

    id: Optional[str] = None
    scholarship_id: str
    criterion_type: str
    criterion_value: str
    is_mandatory: bool = True


class EligibilityFilterResult(BaseModel):
    """Result of filtering a scholarship for student eligibility."""

    scholarship_id: str
    is_eligible: bool
    mandatory_met: int = 0
    mandatory_total: int = 0
    failed_criteria: list[str] = Field(default_factory=list)
