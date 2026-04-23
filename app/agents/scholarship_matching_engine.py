"""ReAct Scholarship Matching Engine.

Implements the Reason-Act-Observe pattern for explainable scholarship matching:
- Reason: Evaluate each scholarship against student profile using 4 dimensions + eligibility
- Act: Score and rank scholarships, mark decisions (recommend/consider/filter_out)
- Observe: Generate decision trace, evidence, and eligibility checks

This is the core component that makes scholarship matching transparent and auditable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from app.agents.eligibility_checker import EligibilityChecker, EligibilityResult
from app.config import settings
from app.core.logging import get_logger
from app.utils.region_mapping import REGION_TO_COUNTRIES, entity_matches_region

logger = get_logger(__name__)


DECISION_RECOMMEND = "recommend"
DECISION_CONSIDER = "consider"
DECISION_FILTER_OUT = "filter_out"

RECOMMEND_THRESHOLD = 0.70
CONSIDER_THRESHOLD = 0.50


@dataclass
class MatchScores:
    """4-dimension match scores with evidence."""

    university_alignment: float = 0.0
    field_alignment: float = 0.0
    degree_alignment: float = 0.0
    geographic_alignment: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "university_alignment": round(self.university_alignment, 3),
            "field_alignment": round(self.field_alignment, 3),
            "degree_alignment": round(self.degree_alignment, 3),
            "geographic_alignment": round(self.geographic_alignment, 3),
        }


@dataclass
class MatchEvidence:
    """Evidence strings explaining each dimension score."""

    university_alignment: str = ""
    field_alignment: str = ""
    degree_alignment: str = ""
    geographic_alignment: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "university_alignment": self.university_alignment,
            "field_alignment": self.field_alignment,
            "degree_alignment": self.degree_alignment,
            "geographic_alignment": self.geographic_alignment,
        }


@dataclass
class ScholarshipMatchResult:
    """Complete match result for a single scholarship."""

    scholarship_id: str
    scholarship_name: str
    provider: str
    amount: str
    deadline: Optional[str]
    composite_score: float
    rank: Optional[int]
    decision: str
    match_scores: MatchScores
    match_evidence: MatchEvidence
    eligibility_check: EligibilityResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "scholarship_id": self.scholarship_id,
            "scholarship_name": self.scholarship_name,
            "provider": self.provider,
            "amount": self.amount,
            "deadline": self.deadline,
            "composite_score": round(self.composite_score, 3),
            "rank": self.rank,
            "decision": self.decision,
            "match_scores": self.match_scores.to_dict(),
            "match_evidence": self.match_evidence.to_dict(),
            "eligibility_check": self.eligibility_check.to_dict(),
        }


@dataclass
class ReactDecisionTrace:
    """Decision trace for a single scholarship."""

    decision: str
    reasons: list[str]
    composite_score: float
    eligibility_status: str
    rank: Optional[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reasons": self.reasons,
            "composite_score": round(self.composite_score, 3),
            "eligibility_status": self.eligibility_status,
            "rank": self.rank,
        }


@dataclass
class ReactMatchingResult:
    """Complete ReAct matching result."""

    react_decision_trace: dict[str, ReactDecisionTrace] = field(default_factory=dict)
    ranked_scholarships: list[ScholarshipMatchResult] = field(default_factory=list)
    filters_applied: list[str] = field(default_factory=list)
    confidence_map: dict[str, float] = field(default_factory=dict)
    eligibility_summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "react_decision_trace": {k: v.to_dict() for k, v in self.react_decision_trace.items()},
            "ranked_scholarships": [s.to_dict() for s in self.ranked_scholarships],
            "filters_applied": self.filters_applied,
            "confidence_map": {k: round(v, 3) for k, v in self.confidence_map.items()},
            "eligibility_summary": self.eligibility_summary,
        }


class ScholarshipMatchingEngine:
    """ReAct-pattern matching engine for explainable scholarship discovery.

    Implements Reason-Act-Observe cycle:
    1. REASON: For each scholarship, evaluate against student profile
    2. ACT: Calculate 4-dimension scores, check eligibility, make decision
    3. OBSERVE: Record decision trace with evidence and reasoning
    """

    ACRONYM_STOPWORDS = {"and", "for", "of", "the", "to", "in"}

    DEGREE_MAP = {
        "bachelor": "bachelor",
        "undergraduate": "bachelor",
        "bsc": "bachelor",
        "ba": "bachelor",
        "bachelors": "bachelor",
        "master": "master",
        "masters": "master",
        "ms": "master",
        "msc": "master",
        "ma": "master",
        "mba": "master",
        "graduate": "master",
        "postgraduate": "master",
        "phd": "phd",
        "doctoral": "phd",
        "doctorate": "phd",
        "postdoc": "phd",
        "postdoctoral": "phd",
        "research": "phd",
    }

    def __init__(self, weights: Optional[dict[str, int]] = None):
        """Initialize engine with optional custom weights.

        Args:
            weights: Dict with keys 'university', 'field', 'degree', 'geographic'.
                     If None, uses settings.get_linking_weights().
        """
        self.weights = weights or settings.get_linking_weights()
        self.eligibility_checker = EligibilityChecker()

    def apply_react_pattern(
        self,
        scholarships: list[dict[str, Any]],
        student_profile: dict[str, Any],
        program_context: Optional[dict[str, Any]] = None,
        criteria_by_scholarship: Optional[dict[str, list[dict[str, Any]]]] = None,
    ) -> ReactMatchingResult:
        """Apply Reason-Act-Observe pattern for scholarship matching.

        Args:
            scholarships: List of scholarship dicts from database
            student_profile: Student profile with gpa, nationality, field_of_study, etc.
            program_context: Optional program metadata for program-specific matching
            criteria_by_scholarship: Optional pre-loaded criteria keyed by scholarship_id

        Returns:
            ReactMatchingResult with complete decision trace and ranked scholarships
        """
        criteria_map = criteria_by_scholarship or {}
        filters_applied: list[str] = []
        decision_trace: dict[str, ReactDecisionTrace] = {}
        confidence_map: dict[str, float] = {}
        results: list[ScholarshipMatchResult] = []

        filters_applied.append(f"Student profile: {self._summarize_profile(student_profile)}")
        filters_applied.append(f"Total scholarships evaluated: {len(scholarships)}")

        fully_eligible = 0
        partially_eligible = 0
        ineligible = 0
        filtered_by_score = 0

        for scholarship in scholarships:
            scholarship_id = scholarship.get("id", "")
            criteria = criteria_map.get(scholarship_id)

            match_scores, match_evidence = self._calculate_match_with_evidence(
                scholarship, student_profile, program_context
            )

            composite_score = self._calculate_composite_score(match_scores)

            eligibility = self.eligibility_checker.check_eligibility(scholarship, student_profile, criteria)

            decision, reasons = self._make_decision(composite_score, eligibility, match_scores, match_evidence)

            if eligibility.is_eligible:
                if not eligibility.missing_info:
                    fully_eligible += 1
                else:
                    partially_eligible += 1
            else:
                ineligible += 1

            if decision == DECISION_FILTER_OUT and composite_score < CONSIDER_THRESHOLD:
                filtered_by_score += 1

            eligibility_status = "eligible" if eligibility.is_eligible else "ineligible"
            if eligibility.missing_info and not eligibility.reasons_ineligible:
                eligibility_status = "unknown"

            decision_trace[scholarship_id] = ReactDecisionTrace(
                decision=decision,
                reasons=reasons,
                composite_score=composite_score,
                eligibility_status=eligibility_status,
                rank=None,
            )
            confidence_map[scholarship_id] = composite_score

            amount_str = self._format_amount(scholarship)
            deadline_str = self._format_deadline(scholarship)

            results.append(
                ScholarshipMatchResult(
                    scholarship_id=scholarship_id,
                    scholarship_name=scholarship.get("name", ""),
                    provider=scholarship.get("provider", ""),
                    amount=amount_str,
                    deadline=deadline_str,
                    composite_score=composite_score,
                    rank=None,
                    decision=decision,
                    match_scores=match_scores,
                    match_evidence=match_evidence,
                    eligibility_check=eligibility,
                )
            )

        recommended = [r for r in results if r.decision == DECISION_RECOMMEND]
        recommended.sort(key=lambda x: x.composite_score, reverse=True)
        for i, r in enumerate(recommended, 1):
            r.rank = i
            if r.scholarship_id in decision_trace:
                decision_trace[r.scholarship_id].rank = i

        considered = [r for r in results if r.decision == DECISION_CONSIDER]
        considered.sort(key=lambda x: x.composite_score, reverse=True)
        offset = len(recommended)
        for i, r in enumerate(considered, offset + 1):
            r.rank = i
            if r.scholarship_id in decision_trace:
                decision_trace[r.scholarship_id].rank = i

        ranked_scholarships = recommended + considered

        filters_applied.append(f"Fully eligible: {fully_eligible}")
        filters_applied.append(f"Partially eligible (missing info): {partially_eligible}")
        filters_applied.append(f"Ineligible: {ineligible}")
        filters_applied.append(f"Filtered by low match score: {filtered_by_score}")
        filters_applied.append(f"Recommended (score >= {RECOMMEND_THRESHOLD}): {len(recommended)}")
        filters_applied.append(f"Considered (score >= {CONSIDER_THRESHOLD}): {len(considered)}")

        return ReactMatchingResult(
            react_decision_trace=decision_trace,
            ranked_scholarships=ranked_scholarships,
            filters_applied=filters_applied,
            confidence_map=confidence_map,
            eligibility_summary={
                "total_scholarships_evaluated": len(scholarships),
                "fully_eligible": fully_eligible,
                "partially_eligible": partially_eligible,
                "ineligible": ineligible,
            },
        )

    def _calculate_match_with_evidence(
        self,
        scholarship: dict[str, Any],
        student_profile: dict[str, Any],
        program_context: Optional[dict[str, Any]],
    ) -> tuple[MatchScores, MatchEvidence]:
        """Calculate all 4 dimension scores with evidence strings."""
        uni_score, uni_evidence = self._calc_university_match_with_evidence(
            scholarship, student_profile, program_context
        )
        field_score, field_evidence = self._calc_field_match_with_evidence(scholarship, student_profile)
        degree_score, degree_evidence = self._calc_degree_match_with_evidence(scholarship, student_profile)
        geo_score, geo_evidence = self._calc_geographic_match_with_evidence(scholarship, student_profile)

        return (
            MatchScores(
                university_alignment=uni_score,
                field_alignment=field_score,
                degree_alignment=degree_score,
                geographic_alignment=geo_score,
            ),
            MatchEvidence(
                university_alignment=uni_evidence,
                field_alignment=field_evidence,
                degree_alignment=degree_evidence,
                geographic_alignment=geo_evidence,
            ),
        )

    def _calc_university_match_with_evidence(
        self,
        scholarship: dict[str, Any],
        student_profile: dict[str, Any],
        program_context: Optional[dict[str, Any]],
    ) -> tuple[float, str]:
        """Calculate university alignment score with evidence."""
        student_university = student_profile.get("university") or student_profile.get("current_institution")
        if program_context:
            student_university = program_context.get("university_name") or student_university

        provider = scholarship.get("provider", "")
        scholarship_name = scholarship.get("name", "")

        if not student_university:
            return 0.5, "University not specified in profile; neutral score applied"

        normalized_student = self._normalize_text(student_university)
        student_tokens = normalized_student.split()
        student_acronym = self._acronym(student_tokens)

        candidates = [
            (provider, "provider"),
            (scholarship_name, "scholarship name"),
        ]

        for candidate, source in candidates:
            normalized_candidate = self._normalize_text(candidate)
            if not normalized_candidate:
                continue

            if normalized_candidate == normalized_student:
                return 1.0, f"Perfect match: Student at '{student_university}', scholarship {source} is '{candidate}'"

            if normalized_candidate in normalized_student or normalized_student in normalized_candidate:
                score = 1.0 if source == "provider" else 0.85
                return (
                    score,
                    f"Substring match: Student's '{student_university}' matches scholarship {source} '{candidate}'",
                )

            candidate_tokens = normalized_candidate.split()

            if len(candidate_tokens) == 1 and len(candidate_tokens[0]) <= 8:
                if candidate_tokens[0] == student_acronym:
                    return (
                        1.0,
                        f"Acronym match: Student at '{student_university}' ({student_acronym}) matches {source} '{candidate}'",
                    )

            if len(student_tokens) == 1 and len(student_tokens[0]) <= 8:
                candidate_acronym = self._acronym(candidate_tokens)
                if student_tokens[0] == candidate_acronym:
                    return (
                        1.0,
                        f"Acronym match: Student at '{student_university}' matches {source} acronym ({candidate_acronym})",
                    )

            overlap = set(candidate_tokens) & set(student_tokens)
            if len(overlap) >= 2:
                score = 0.9 if source == "provider" else 0.75
                return (
                    score,
                    f"Partial match: '{student_university}' shares keywords with {source} '{candidate}' ({', '.join(overlap)})",
                )

        return 0.0, f"No match: Student at '{student_university}', scholarship provider is '{provider}'"

    def _calc_field_match_with_evidence(
        self,
        scholarship: dict[str, Any],
        student_profile: dict[str, Any],
    ) -> tuple[float, str]:
        """Calculate field alignment score with evidence."""
        scholarship_fields = self._criterion_values(scholarship, "field_of_study")

        if not scholarship_fields:
            return 1.0, "Scholarship open to all fields of study"

        student_field = student_profile.get("field_of_study")

        if not student_field:
            return 0.5, f"Field of study not specified; scholarship targets: {', '.join(scholarship_fields)}"

        normalized_student = self._normalize_text(student_field)
        if not normalized_student:
            return 0.5, f"Invalid field of study format; scholarship targets: {', '.join(scholarship_fields)}"

        student_keywords = set(normalized_student.split())

        best_score = 0.0
        best_evidence = ""

        for sch_field in scholarship_fields:
            normalized_field = self._normalize_text(sch_field)
            if not normalized_field:
                continue

            if normalized_field == normalized_student:
                return (
                    1.0,
                    f"Perfect field match: Student's '{student_field}' exactly matches scholarship field '{sch_field}'",
                )

            if normalized_field in normalized_student or normalized_student in normalized_field:
                if 0.9 > best_score:
                    best_score = 0.9
                    best_evidence = f"Strong field match: Student's '{student_field}' aligns with '{sch_field}'"
                continue

            scholarship_keywords = set(normalized_field.split())
            overlap = scholarship_keywords & student_keywords
            union = scholarship_keywords | student_keywords

            if union:
                jaccard = len(overlap) / len(union)
                if jaccard > best_score:
                    best_score = jaccard
                    if jaccard >= 0.5:
                        best_evidence = f"Keyword overlap: Student's '{student_field}' shares terms with '{sch_field}' ({', '.join(overlap)})"
                    else:
                        best_evidence = (
                            f"Weak match: Student's '{student_field}' has limited overlap with '{sch_field}'"
                        )

        if best_score > 0:
            return best_score, best_evidence

        return (
            0.0,
            f"No match: Student's '{student_field}' doesn't match scholarship fields: {', '.join(scholarship_fields)}",
        )

    def _calc_degree_match_with_evidence(
        self,
        scholarship: dict[str, Any],
        student_profile: dict[str, Any],
    ) -> tuple[float, str]:
        """Calculate degree alignment score with evidence."""
        scholarship_degrees = self._criterion_values(scholarship, "degree_level")

        if not scholarship_degrees:
            return 1.0, "Scholarship open to all degree levels"

        student_degree = student_profile.get("degree_type") or student_profile.get("target_degree_level")

        if not student_degree:
            return 0.5, f"Degree level not specified; scholarship targets: {', '.join(scholarship_degrees)}"

        normalized_student = self.DEGREE_MAP.get(student_degree.lower(), student_degree.lower())

        normalized_scholarship = [
            self.DEGREE_MAP.get(self._normalize_text(d), self._normalize_text(d)) for d in scholarship_degrees
        ]

        if normalized_student in normalized_scholarship:
            return (
                1.0,
                f"Perfect degree match: Student's '{student_degree}' matches eligible levels: {', '.join(scholarship_degrees)}",
            )

        if student_degree.lower() in [d.lower() for d in scholarship_degrees]:
            return 1.0, f"Exact degree match: Student's '{student_degree}' is in eligible levels"

        return (
            0.0,
            f"Degree mismatch: Student's '{student_degree}' not in eligible levels: {', '.join(scholarship_degrees)}",
        )

    def _calc_geographic_match_with_evidence(
        self,
        scholarship: dict[str, Any],
        student_profile: dict[str, Any],
    ) -> tuple[float, str]:
        """Calculate geographic alignment score with evidence."""
        scholarship_regions = self._criterion_values(scholarship, "region")
        scholarship_nationalities = self._criterion_values(scholarship, "nationality")

        if not scholarship_regions and not scholarship_nationalities:
            return 1.0, "Scholarship open to all nationalities/regions"

        student_nationality = student_profile.get("nationality")

        if not student_nationality:
            restrictions = scholarship_regions + scholarship_nationalities
            return 0.5, f"Nationality not specified; scholarship targets: {', '.join(restrictions)}"

        for region in scholarship_regions:
            if entity_matches_region(student_nationality, region):
                region_lower = region.lower()
                countries = REGION_TO_COUNTRIES.get(region_lower)
                if countries:
                    return 1.0, f"Regional match: '{student_nationality}' is in eligible region '{region}'"
                return 1.0, f"Geographic match: '{student_nationality}' matches '{region}'"

        normalized_nationality = self._normalize_text(student_nationality)
        for nationality in scholarship_nationalities:
            if normalized_nationality == self._normalize_text(nationality):
                return 1.0, f"Nationality match: '{student_nationality}' is explicitly eligible"
            if entity_matches_region(student_nationality, nationality):
                return 1.0, f"Nationality/region match: '{student_nationality}' matches '{nationality}'"

        restrictions = scholarship_regions + scholarship_nationalities
        return (
            0.0,
            f"Geographic restriction: '{student_nationality}' not in eligible regions/nationalities: {', '.join(restrictions)}",
        )

    def _calculate_composite_score(self, scores: MatchScores) -> float:
        """Calculate weighted composite score from 4 dimensions."""
        total_weight = sum(self.weights.values()) or 100
        composite = (
            self.weights["university"] * scores.university_alignment
            + self.weights["field"] * scores.field_alignment
            + self.weights["degree"] * scores.degree_alignment
            + self.weights["geographic"] * scores.geographic_alignment
        ) / total_weight
        return max(0.0, min(1.0, composite))

    def _make_decision(
        self,
        composite_score: float,
        eligibility: EligibilityResult,
        scores: MatchScores,
        evidence: MatchEvidence,
    ) -> tuple[str, list[str]]:
        """Make recommendation decision with reasoning."""
        reasons: list[str] = []

        reasons.append(f"university_alignment: {scores.university_alignment:.2f} ({evidence.university_alignment})")
        reasons.append(f"field_alignment: {scores.field_alignment:.2f} ({evidence.field_alignment})")
        reasons.append(f"degree_alignment: {scores.degree_alignment:.2f} ({evidence.degree_alignment})")
        reasons.append(f"geographic_alignment: {scores.geographic_alignment:.2f} ({evidence.geographic_alignment})")

        if eligibility.reasons_ineligible:
            for reason in eligibility.reasons_ineligible:
                reasons.append(f"INELIGIBLE: {reason}")
            return DECISION_FILTER_OUT, reasons

        if composite_score >= RECOMMEND_THRESHOLD:
            for reason in eligibility.reasons_eligible:
                reasons.append(f"ELIGIBLE: {reason}")
            return DECISION_RECOMMEND, reasons

        if composite_score >= CONSIDER_THRESHOLD:
            if eligibility.missing_info:
                for info in eligibility.missing_info:
                    reasons.append(f"MISSING: {info}")
            return DECISION_CONSIDER, reasons

        reasons.append(f"Low composite score: {composite_score:.2f} < {CONSIDER_THRESHOLD}")
        return DECISION_FILTER_OUT, reasons

    @staticmethod
    def _normalize_text(value: Any) -> str:
        """Lowercase and remove punctuation for lenient text matching."""
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    @classmethod
    def _acronym(cls, tokens: list[str]) -> str:
        """Build an acronym while ignoring common stopwords."""
        return "".join(token[0] for token in tokens if token and token not in cls.ACRONYM_STOPWORDS)

    @staticmethod
    def _eligibility_payload(scholarship: dict[str, Any]) -> dict[str, Any]:
        """Return eligibility JSON as a dict when available."""
        eligibility = scholarship.get("eligibility_criteria") or {}
        if isinstance(eligibility, dict):
            return eligibility
        return {}

    @classmethod
    def _criterion_values(cls, scholarship: dict[str, Any], criterion_type: str) -> list[str]:
        """Extract values from parsed_criteria or legacy flat JSON keys."""
        eligibility = cls._eligibility_payload(scholarship)
        values: list[str] = []

        for criterion in eligibility.get("parsed_criteria") or []:
            if not isinstance(criterion, dict):
                continue
            if criterion.get("criterion_type") == criterion_type or criterion.get("type") == criterion_type:
                raw = criterion.get("criterion_value") or criterion.get("value")
                values.extend(cls._split_values(raw))

        if not values:
            values.extend(cls._split_values(eligibility.get(criterion_type)))

        return cls._unique_strings(values)

    @staticmethod
    def _split_values(value: Any) -> list[str]:
        """Normalize comma/list values into a flat list of strings."""
        if value in (None, "", [], {}):
            return []
        if isinstance(value, list):
            result: list[str] = []
            for item in value:
                result.extend(ScholarshipMatchingEngine._split_values(item))
            return result
        return [part.strip() for part in str(value).split(",") if part.strip()]

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        """Dedupe values case-insensitively while preserving original spelling."""
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = ScholarshipMatchingEngine._normalize_text(value)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(value)
        return result

    @staticmethod
    def _summarize_profile(profile: dict[str, Any]) -> str:
        """Create a human-readable profile summary."""
        parts = []
        if profile.get("degree_type") or profile.get("target_degree_level"):
            parts.append(f"{profile.get('degree_type') or profile.get('target_degree_level')}'s")
        if profile.get("field_of_study"):
            parts.append(f"in {profile['field_of_study']}")
        if profile.get("university") or profile.get("current_institution"):
            parts.append(f"at {profile.get('university') or profile.get('current_institution')}")
        if profile.get("gpa"):
            parts.append(f"GPA {profile['gpa']}")
        if profile.get("nationality"):
            parts.append(f"({profile['nationality']} national)")
        return " ".join(parts) if parts else "incomplete profile"

    @staticmethod
    def _format_amount(scholarship: dict[str, Any]) -> str:
        """Format scholarship amount for display."""
        amount = scholarship.get("funding_amount")
        currency = scholarship.get("currency", "USD")
        if amount:
            try:
                return f"{currency} {float(amount):,.0f}"
            except (ValueError, TypeError):
                return str(amount)
        return "Amount varies"

    @staticmethod
    def _format_deadline(scholarship: dict[str, Any]) -> Optional[str]:
        """Format deadline for display."""
        deadline = scholarship.get("deadline")
        if not deadline:
            return None
        if isinstance(deadline, (date, datetime)):
            return deadline.isoformat() if isinstance(deadline, date) else deadline.date().isoformat()
        return str(deadline)


def apply_react_matching_pattern(
    scholarships: list[dict[str, Any]],
    student_profile: dict[str, Any],
    program_context: Optional[dict[str, Any]] = None,
    matching_weights: Optional[dict[str, int]] = None,
    criteria_by_scholarship: Optional[dict[str, list[dict[str, Any]]]] = None,
) -> dict[str, Any]:
    """Convenience function to apply ReAct matching pattern.

    This is the main entry point for the matching engine.

    Args:
        scholarships: List of scholarship dicts from database
        student_profile: Student profile with gpa, nationality, field_of_study, etc.
        program_context: Optional program metadata for program-specific matching
        matching_weights: Optional custom weights (defaults to settings)
        criteria_by_scholarship: Optional pre-loaded criteria keyed by scholarship_id

    Returns:
        Dict with react_decision_trace, ranked_scholarships, filters_applied,
        confidence_map, and eligibility_summary
    """
    engine = ScholarshipMatchingEngine(weights=matching_weights)
    result = engine.apply_react_pattern(
        scholarships=scholarships,
        student_profile=student_profile,
        program_context=program_context,
        criteria_by_scholarship=criteria_by_scholarship,
    )
    return result.to_dict()
