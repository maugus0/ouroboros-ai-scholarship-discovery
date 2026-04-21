"""Data-access layer for the eligibility_criteria table (raw SQL, aiomysql)."""

from typing import Any

from app.core.logging import get_logger
from app.repositories.mysql_base import MySQLBaseRepository
from app.utils.helpers import generate_uuid

logger = get_logger(__name__)


class EligibilityCriteriaRepository(MySQLBaseRepository):
    """CRUD operations on the ``eligibility_criteria`` table."""

    async def create(self, data: dict[str, Any]) -> str:
        """Backward-compatible alias used by older service code."""
        return await self.create_criterion(data)

    async def create_criterion(self, data: dict[str, Any]) -> str:
        """Insert a new eligibility criterion and return its UUID."""
        criterion_id = generate_uuid()
        query = """
            INSERT INTO eligibility_criteria (
                id, scholarship_id, criterion_type, criterion_value, is_mandatory
            ) VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            criterion_id,
            data["scholarship_id"],
            data["criterion_type"],
            data["criterion_value"],
            data.get("is_mandatory", True),
        )
        await self.execute_write(query, params)
        return criterion_id

    async def bulk_create_criteria(self, criteria: list[dict[str, Any]]) -> int:
        """Insert multiple criteria for a scholarship. Returns count inserted."""
        count = 0
        for criterion in criteria:
            await self.create_criterion(criterion)
            count += 1
        logger.info("criteria_bulk_created", count=count)
        return count

    async def get_by_scholarship_id(self, scholarship_id: str) -> list[dict[str, Any]]:
        """Return all criteria for a scholarship."""
        query = "SELECT * FROM eligibility_criteria WHERE scholarship_id = %s ORDER BY criterion_type"
        return await self.execute_query(query, (scholarship_id,))

    async def get_mandatory_by_scholarship_id(self, scholarship_id: str) -> list[dict[str, Any]]:
        """Return only mandatory criteria for a scholarship."""
        query = """
            SELECT * FROM eligibility_criteria
            WHERE scholarship_id = %s AND is_mandatory = TRUE
            ORDER BY criterion_type
        """
        return await self.execute_query(query, (scholarship_id,))

    async def delete_by_scholarship_id(self, scholarship_id: str) -> int:
        """Delete all criteria for a scholarship (used before re-crawl refresh)."""
        query = "DELETE FROM eligibility_criteria WHERE scholarship_id = %s"
        rows = await self.execute_write(query, (scholarship_id,))
        logger.info("criteria_deleted", scholarship_id=scholarship_id, count=rows)
        return rows
