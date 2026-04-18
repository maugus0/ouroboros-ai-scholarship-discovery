"""Eligibility Filtering Service.

Filters scholarships based on strict binary matching against student profile.
Criteria are loaded from the ``eligibility_criteria`` table (mandatory vs optional).
"""

from typing import Any

from app.core.logging import get_logger
from app.repositories.mysql_eligibility_criteria_repo import EligibilityCriteriaRepository
from app.utils.region_mapping import entity_matches_region

logger = get_logger(__name__)


class EligibilityFilterService:
    """Filters scholarships to only those where a student meets all mandatory criteria."""

    def __init__(self):
        self.criteria_repo = EligibilityCriteriaRepository()

    async def filter_eligible(
        self,
        student_profile: dict[str, Any],
        scholarships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Filter scholarships to only those where student meets ALL mandatory criteria."""
        eligible = []

        for scholarship in scholarships:
            criteria = await self.criteria_repo.get_by_scholarship_id(scholarship["id"])

            if self._meets_all_mandatory(student_profile, criteria):
                eligible.append(scholarship)

        return eligible

    def _meets_all_mandatory(self, profile: dict[str, Any], criteria: list[dict[str, Any]]) -> bool:
        """Check if student meets all mandatory criteria."""
        mandatory_criteria = [criterion for criterion in criteria if criterion.get("is_mandatory", True)]
        language_criteria = [
            criterion for criterion in mandatory_criteria if criterion.get("criterion_type") == "language_test"
        ]

        if language_criteria and not any(self._meets_criterion(profile, criterion) for criterion in language_criteria):
            return False

        for criterion in mandatory_criteria:
            if criterion.get("criterion_type") == "language_test":
                continue
            if not criterion.get("is_mandatory", True):
                continue

            if not self._meets_criterion(profile, criterion):
                return False

        return True

    def _meets_criterion(self, profile: dict[str, Any], criterion: dict[str, Any]) -> bool:
        """Check if student meets a single criterion."""
        # pylint: disable=too-many-return-statements,too-many-branches
        ctype = criterion["criterion_type"]
        value = criterion["criterion_value"]

        if ctype == "min_gpa":
            student_gpa = profile.get("gpa", 0.0)
            if student_gpa is None:
                return True
            try:
                required_gpa = float(value)
                return float(student_gpa) >= required_gpa
            except (ValueError, TypeError):
                return True

        elif ctype == "nationality":
            student_nationality = profile.get("nationality", "")
            if not student_nationality:
                return True
            allowed = [n.strip().lower() for n in value.split(",")]
            return student_nationality.lower() in allowed

        elif ctype == "region":
            student_nationality = profile.get("nationality", "")
            if not student_nationality:
                return True
            return self._nationality_in_region(student_nationality, value)

        elif ctype == "field_of_study":
            student_field = profile.get("field_of_study", "")
            if not student_field:
                return True
            allowed = [f.strip().lower() for f in value.split(",")]
            return student_field.lower() in allowed

        elif ctype == "degree_level":
            student_degree = profile.get("degree_type", "")
            if not student_degree:
                return True
            allowed = [d.strip().lower() for d in value.split(",")]
            return student_degree.lower() in allowed

        elif ctype == "language_test":
            student_test = profile.get("language_test", "")
            if not student_test:
                return True
            return self._meets_language_requirement(student_test, value)

        logger.warning("unknown_criterion_type", criterion_type=ctype)
        return True

    @staticmethod
    def _nationality_in_region(nationality: str, region: str) -> bool:
        """Check if nationality belongs to region."""
        return entity_matches_region(nationality, region)

    @staticmethod
    def _meets_language_requirement(student_test: str, required_test: str) -> bool:
        """Check if student's language test meets requirement."""
        try:
            student_parts = student_test.split()
            required_parts = required_test.split()

            if student_parts[0].upper() != required_parts[0].upper():
                return False

            student_score = float(student_parts[1])
            required_score = float(required_parts[1])

            return student_score >= required_score
        except (IndexError, ValueError):
            logger.warning("language_test_parse_failed", student=student_test, required=required_test)
            return True
