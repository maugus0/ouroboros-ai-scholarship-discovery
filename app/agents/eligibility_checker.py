"""Comprehensive Eligibility Checking with Explainability.

Provides detailed eligibility analysis with clear reasons for eligible/ineligible/missing info.
This is the core component that makes scholarship eligibility transparent and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from app.core.logging import get_logger
from app.utils.region_mapping import REGION_TO_COUNTRIES, entity_matches_region

logger = get_logger(__name__)


@dataclass
class EligibilityResult:
    """Complete eligibility check result with detailed reasons."""

    is_eligible: bool
    reasons_eligible: list[str] = field(default_factory=list)
    reasons_ineligible: list[str] = field(default_factory=list)
    missing_info: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "is_eligible": self.is_eligible,
            "reasons_eligible": self.reasons_eligible,
            "reasons_ineligible": self.reasons_ineligible,
            "missing_info": self.missing_info,
            "confidence": round(self.confidence, 3),
        }


class EligibilityChecker:
    """Comprehensive eligibility checking with detailed explanations.

    Evaluates student profile against scholarship criteria and provides:
    - Clear reasons why student qualifies
    - Clear reasons why student doesn't qualify
    - Missing information that prevents full determination
    """

    DEGREE_ALIASES = {
        "bachelor": ["bachelor", "bsc", "ba", "undergraduate", "bachelors"],
        "master": ["master", "masters", "ms", "msc", "ma", "mba", "graduate", "postgraduate"],
        "phd": ["phd", "doctoral", "doctorate", "postdoc", "postdoctoral", "research"],
    }

    def __init__(self):
        self._degree_map = self._build_degree_map()

    def _build_degree_map(self) -> dict[str, str]:
        """Build reverse mapping from aliases to canonical degree names."""
        mapping = {}
        for canonical, aliases in self.DEGREE_ALIASES.items():
            for alias in aliases:
                mapping[alias.lower()] = canonical
        return mapping

    def check_eligibility(
        self,
        scholarship: dict[str, Any],
        student_profile: dict[str, Any],
        criteria: Optional[list[dict[str, Any]]] = None,
    ) -> EligibilityResult:
        """Check comprehensive eligibility against all criteria.

        Args:
            scholarship: Scholarship data including eligibility_criteria JSON
            student_profile: Student profile with gpa, nationality, field_of_study, etc.
            criteria: Optional pre-loaded criteria from eligibility_criteria table

        Returns:
            EligibilityResult with detailed reasons
        """
        reasons_eligible: list[str] = []
        reasons_ineligible: list[str] = []
        missing_info: list[str] = []

        self._check_gpa(scholarship, student_profile, criteria, reasons_eligible, reasons_ineligible, missing_info)
        self._check_degree_level(
            scholarship, student_profile, criteria, reasons_eligible, reasons_ineligible, missing_info
        )
        self._check_field_of_study(
            scholarship, student_profile, criteria, reasons_eligible, reasons_ineligible, missing_info
        )
        self._check_nationality(
            scholarship, student_profile, criteria, reasons_eligible, reasons_ineligible, missing_info
        )
        self._check_region(scholarship, student_profile, criteria, reasons_eligible, reasons_ineligible, missing_info)
        self._check_language_test(
            scholarship, student_profile, criteria, reasons_eligible, reasons_ineligible, missing_info
        )
        self._check_deadline(scholarship, reasons_eligible, reasons_ineligible, missing_info)

        is_eligible = len(reasons_ineligible) == 0 and len(missing_info) == 0
        confidence = self._calculate_confidence(reasons_eligible, reasons_ineligible, missing_info)

        return EligibilityResult(
            is_eligible=is_eligible,
            reasons_eligible=reasons_eligible,
            reasons_ineligible=reasons_ineligible,
            missing_info=missing_info,
            confidence=confidence,
        )

    def _get_criterion_value(
        self,
        scholarship: dict[str, Any],
        criteria: Optional[list[dict[str, Any]]],
        criterion_type: str,
    ) -> tuple[Optional[str], bool]:
        """Extract criterion value from criteria list or scholarship JSON.

        Returns:
            Tuple of (value, is_mandatory)
        """
        if criteria:
            for c in criteria:
                if c.get("criterion_type") == criterion_type:
                    return c.get("criterion_value"), c.get("is_mandatory", True)

        eligibility = scholarship.get("eligibility_criteria") or {}
        if isinstance(eligibility, dict):
            for c in eligibility.get("parsed_criteria") or []:
                if isinstance(c, dict) and (
                    c.get("criterion_type") == criterion_type or c.get("type") == criterion_type
                ):
                    return c.get("criterion_value") or c.get("value"), c.get("is_mandatory", True)
            if criterion_type in eligibility:
                return eligibility[criterion_type], True

        return None, False

    def _check_gpa(
        self,
        scholarship: dict[str, Any],
        profile: dict[str, Any],
        criteria: Optional[list[dict[str, Any]]],
        eligible: list[str],
        ineligible: list[str],
        missing: list[str],
    ) -> None:
        """Check GPA requirement."""
        required_gpa_str, is_mandatory = self._get_criterion_value(scholarship, criteria, "min_gpa")

        if not required_gpa_str:
            return

        try:
            required_gpa = float(required_gpa_str)
        except (ValueError, TypeError):
            return

        student_gpa = profile.get("gpa")
        student_scale = profile.get("gpa_scale", 4.0) or 4.0

        if student_gpa is None:
            if is_mandatory:
                missing.append(f"GPA not provided; scholarship requires minimum {required_gpa:.2f}")
            return

        try:
            student_gpa_float = float(student_gpa)
        except (ValueError, TypeError):
            missing.append(f"Invalid GPA format: {student_gpa}")
            return

        normalized_gpa = student_gpa_float * (4.0 / student_scale) if student_scale != 4.0 else student_gpa_float

        if normalized_gpa >= required_gpa:
            eligible.append(
                f"GPA {student_gpa_float:.2f} (normalized: {normalized_gpa:.2f}) meets minimum {required_gpa:.2f}"
            )
        elif is_mandatory:
            ineligible.append(
                f"GPA {student_gpa_float:.2f} (normalized: {normalized_gpa:.2f}) below minimum {required_gpa:.2f}"
            )

    def _check_degree_level(
        self,
        scholarship: dict[str, Any],
        profile: dict[str, Any],
        criteria: Optional[list[dict[str, Any]]],
        eligible: list[str],
        ineligible: list[str],
        missing: list[str],
    ) -> None:
        """Check degree level requirement."""
        required_degrees_str, is_mandatory = self._get_criterion_value(scholarship, criteria, "degree_level")

        if not required_degrees_str:
            return

        allowed_degrees = [d.strip().lower() for d in required_degrees_str.split(",") if d.strip()]
        if not allowed_degrees:
            return

        student_degree = profile.get("degree_type") or profile.get("target_degree_level")

        if not student_degree:
            if is_mandatory:
                missing.append(f"Degree level not provided; scholarship requires: {', '.join(allowed_degrees)}")
            return

        student_canonical = self._degree_map.get(student_degree.lower(), student_degree.lower())
        allowed_canonical = [self._degree_map.get(d, d) for d in allowed_degrees]

        if student_canonical in allowed_canonical or student_degree.lower() in allowed_degrees:
            eligible.append(f"Degree level '{student_degree}' matches eligible levels: {', '.join(allowed_degrees)}")
        elif is_mandatory:
            ineligible.append(f"Degree level '{student_degree}' not in eligible levels: {', '.join(allowed_degrees)}")

    def _check_field_of_study(
        self,
        scholarship: dict[str, Any],
        profile: dict[str, Any],
        criteria: Optional[list[dict[str, Any]]],
        eligible: list[str],
        ineligible: list[str],
        missing: list[str],
    ) -> None:
        """Check field of study requirement."""
        required_fields_str, is_mandatory = self._get_criterion_value(scholarship, criteria, "field_of_study")

        if not required_fields_str:
            return

        allowed_fields = [f.strip().lower() for f in required_fields_str.split(",") if f.strip()]
        if not allowed_fields:
            return

        student_field = profile.get("field_of_study")

        if not student_field:
            if is_mandatory:
                missing.append(f"Field of study not provided; scholarship requires: {', '.join(allowed_fields)}")
            return

        student_field_lower = student_field.lower()

        if student_field_lower in allowed_fields:
            eligible.append(f"Field of study '{student_field}' matches eligible fields")
        elif any(af in student_field_lower or student_field_lower in af for af in allowed_fields):
            eligible.append(f"Field of study '{student_field}' partially matches eligible fields")
        elif is_mandatory:
            ineligible.append(f"Field of study '{student_field}' not in eligible fields: {', '.join(allowed_fields)}")

    def _check_nationality(
        self,
        scholarship: dict[str, Any],
        profile: dict[str, Any],
        criteria: Optional[list[dict[str, Any]]],
        eligible: list[str],
        ineligible: list[str],
        missing: list[str],
    ) -> None:
        """Check nationality requirement."""
        required_nationalities_str, is_mandatory = self._get_criterion_value(scholarship, criteria, "nationality")

        if not required_nationalities_str:
            return

        allowed_nationalities = [n.strip().lower() for n in required_nationalities_str.split(",") if n.strip()]
        if not allowed_nationalities:
            return

        student_nationality = profile.get("nationality")

        if not student_nationality:
            if is_mandatory:
                missing.append(f"Nationality not provided; scholarship requires: {', '.join(allowed_nationalities)}")
            return

        student_nationality_lower = student_nationality.lower()

        if student_nationality_lower in allowed_nationalities:
            eligible.append(f"Nationality '{student_nationality}' is eligible")
        elif is_mandatory:
            ineligible.append(
                f"Nationality '{student_nationality}' not in eligible nationalities: {', '.join(allowed_nationalities)}"
            )

    def _check_region(
        self,
        scholarship: dict[str, Any],
        profile: dict[str, Any],
        criteria: Optional[list[dict[str, Any]]],
        eligible: list[str],
        ineligible: list[str],
        missing: list[str],
    ) -> None:
        """Check regional eligibility using region mappings."""
        required_regions_str, is_mandatory = self._get_criterion_value(scholarship, criteria, "region")

        if not required_regions_str:
            return

        allowed_regions = [r.strip() for r in required_regions_str.split(",") if r.strip()]
        if not allowed_regions:
            return

        student_nationality = profile.get("nationality")

        if not student_nationality:
            if is_mandatory:
                missing.append(f"Nationality not provided; scholarship requires regions: {', '.join(allowed_regions)}")
            return

        for region in allowed_regions:
            if entity_matches_region(student_nationality, region):
                region_lower = region.lower()
                countries = REGION_TO_COUNTRIES.get(region_lower)
                if countries:
                    eligible.append(f"Nationality '{student_nationality}' is in eligible region '{region}'")
                else:
                    eligible.append(f"Nationality '{student_nationality}' matches '{region}'")
                return

        if is_mandatory:
            ineligible.append(
                f"Nationality '{student_nationality}' not in eligible regions: {', '.join(allowed_regions)}"
            )

    def _check_language_test(
        self,
        scholarship: dict[str, Any],
        profile: dict[str, Any],
        criteria: Optional[list[dict[str, Any]]],
        eligible: list[str],
        ineligible: list[str],
        missing: list[str],
    ) -> None:
        """Check language test requirement."""
        required_test_str, is_mandatory = self._get_criterion_value(scholarship, criteria, "language_test")

        if not required_test_str:
            return

        student_test = profile.get("language_test")

        if not student_test:
            if is_mandatory:
                missing.append(f"Language test not provided; scholarship requires: {required_test_str}")
            return

        try:
            student_parts = student_test.split()
            required_parts = required_test_str.split()

            if len(student_parts) < 2 or len(required_parts) < 2:
                missing.append(
                    f"Invalid language test format: student='{student_test}', required='{required_test_str}'"
                )
                return

            student_test_name = student_parts[0].upper()
            required_test_name = required_parts[0].upper()

            if student_test_name != required_test_name:
                if is_mandatory:
                    ineligible.append(
                        f"Language test type '{student_test_name}' doesn't match required '{required_test_name}'"
                    )
                return

            student_score = float(student_parts[1])
            required_score = float(required_parts[1])

            if student_score >= required_score:
                eligible.append(
                    f"Language test {student_test_name} score {student_score} meets minimum {required_score}"
                )
            elif is_mandatory:
                ineligible.append(
                    f"Language test {student_test_name} score {student_score} below minimum {required_score}"
                )

        except (IndexError, ValueError) as exc:
            logger.warning(
                "language_test_parse_failed", student=student_test, required=required_test_str, error=str(exc)
            )
            missing.append(f"Could not parse language test: student='{student_test}', required='{required_test_str}'")

    def _check_deadline(
        self,
        scholarship: dict[str, Any],
        eligible: list[str],
        ineligible: list[str],
        missing: list[str],
    ) -> None:
        """Check if scholarship deadline has passed."""
        deadline = scholarship.get("deadline")

        if not deadline:
            return

        today = date.today()

        if isinstance(deadline, str):
            try:
                deadline = datetime.strptime(deadline, "%Y-%m-%d").date()
            except ValueError:
                try:
                    deadline = datetime.fromisoformat(deadline).date()
                except ValueError:
                    return
        elif isinstance(deadline, datetime):
            deadline = deadline.date()
        elif not isinstance(deadline, date):
            return

        if deadline < today:
            ineligible.append(f"Deadline {deadline.isoformat()} has passed (today: {today.isoformat()})")
        else:
            days_remaining = (deadline - today).days
            if days_remaining <= 14:
                eligible.append(f"Deadline {deadline.isoformat()} is in {days_remaining} days — apply soon!")
            else:
                eligible.append(f"Deadline {deadline.isoformat()} is open ({days_remaining} days remaining)")

    def _calculate_confidence(
        self,
        eligible: list[str],
        ineligible: list[str],
        missing: list[str],
    ) -> float:
        """Calculate confidence in eligibility determination.

        Higher confidence when we have complete information.
        Lower confidence when profile data is missing.
        """
        total_checks = len(eligible) + len(ineligible) + len(missing)
        if total_checks == 0:
            return 1.0

        if len(ineligible) > 0:
            return 1.0 - (len(missing) * 0.1)

        determined = len(eligible) + len(ineligible)
        confidence = determined / total_checks

        return max(0.0, min(1.0, confidence))
