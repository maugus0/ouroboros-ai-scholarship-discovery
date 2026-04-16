"""Data-access layer for the scholarships table (raw SQL, aiomysql)."""

import json
from typing import Any

from app.core.logging import get_logger
from app.repositories.mysql_base import MySQLBaseRepository
from app.utils.helpers import generate_uuid

logger = get_logger(__name__)


class ScholarshipRepository(MySQLBaseRepository):
    """CRUD operations on the ``scholarships`` table."""

    _PERSISTED_FIELDS = {
        "name",
        "provider",
        "funding_amount",
        "currency",
        "deadline",
        "description",
        "eligibility_criteria",
        "application_requirements",
        "source_url",
        "crawled_at",
        "is_active",
    }

    async def create_scholarship(self, data: dict[str, Any]) -> str:
        """Insert a new scholarship and return its UUID."""
        scholarship_id = data.get("id") or generate_uuid()
        query = """
            INSERT INTO scholarships (
                id, name, provider, funding_amount, currency,
                deadline, description, eligibility_criteria,
                application_requirements, source_url, crawled_at, is_active
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s
            )
        """
        params = (
            scholarship_id,
            data["name"],
            data["provider"],
            data.get("funding_amount"),
            data.get("currency"),
            data.get("deadline"),
            data.get("description"),
            json.dumps(data.get("eligibility_criteria")) if data.get("eligibility_criteria") else None,
            json.dumps(data.get("application_requirements")) if data.get("application_requirements") else None,
            data["source_url"],
            data.get("crawled_at"),
            data.get("is_active", True),
        )
        await self.execute_write(query, params)
        logger.info("scholarship_created", scholarship_id=scholarship_id, name=data["name"])
        return scholarship_id

    async def get_by_id(self, scholarship_id: str) -> dict[str, Any] | None:
        """Retrieve a scholarship by UUID."""
        query = "SELECT * FROM scholarships WHERE id = %s"
        return await self.execute_one(query, (scholarship_id,))

    async def get_by_source_url(self, source_url: str) -> dict[str, Any] | None:
        """Retrieve a scholarship by its canonical source URL."""
        query = "SELECT * FROM scholarships WHERE source_url = %s LIMIT 1"
        return await self.execute_one(query, (source_url,))

    async def search_scholarships(
        self,
        provider: str | None = None,
        field: str | None = None,
        scholarship_ids: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Search scholarships with optional filters.

        When ``scholarship_ids`` is set, results are restricted to that ID set (AND with other filters).
        """
        conditions = ["is_active = TRUE"]
        params: list[Any] = []

        if provider:
            conditions.append("provider LIKE %s")
            params.append(f"%{provider}%")

        if field:
            conditions.append("MATCH(name, description) AGAINST(%s IN BOOLEAN MODE)")
            params.append(field)

        if scholarship_ids is not None:
            if not scholarship_ids:
                return []
            placeholders = ", ".join(["%s"] * len(scholarship_ids))
            conditions.append(f"id IN ({placeholders})")
            params.extend(scholarship_ids)

        where_clause = " AND ".join(conditions)
        params.extend([limit, offset])

        query = f"""
            SELECT * FROM scholarships
            WHERE {where_clause}
            ORDER BY deadline ASC, created_at DESC
            LIMIT %s OFFSET %s
        """
        return await self.execute_query(query, tuple(params))

    async def count_scholarships(
        self,
        provider: str | None = None,
        scholarship_ids: list[str] | None = None,
    ) -> int:
        """Count scholarships matching the same filters as :meth:`search_scholarships`."""
        conditions = ["is_active = TRUE"]
        params: list[Any] = []

        if provider:
            conditions.append("provider LIKE %s")
            params.append(f"%{provider}%")

        if scholarship_ids is not None:
            if not scholarship_ids:
                return 0
            placeholders = ", ".join(["%s"] * len(scholarship_ids))
            conditions.append(f"id IN ({placeholders})")
            params.extend(scholarship_ids)

        where_clause = " AND ".join(conditions)
        query = f"SELECT COUNT(*) AS total FROM scholarships WHERE {where_clause}"
        result = await self.execute_one(query, tuple(params))
        return result["total"] if result else 0

    async def get_stale_scholarships(self, staleness_days: int = 30) -> list[dict[str, Any]]:
        """Return scholarships not crawled within the staleness threshold."""
        query = """
            SELECT * FROM scholarships
            WHERE is_active = TRUE
              AND crawled_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY crawled_at ASC
        """
        return await self.execute_query(query, (staleness_days,))

    async def update_scholarship(self, scholarship_id: str, updates: dict[str, Any]) -> int:
        """Update specific fields on a scholarship."""
        if not updates:
            return 0
        json_fields = {"eligibility_criteria", "application_requirements"}
        filtered_updates = {}
        for key, value in updates.items():
            if key not in self._PERSISTED_FIELDS:
                continue
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, (dict, list)) and not value:
                continue
            filtered_updates[key] = value
        if not filtered_updates:
            logger.info("scholarship_update_skipped_no_persisted_fields", scholarship_id=scholarship_id)
            return 0
        set_clauses = []
        params: list[Any] = []
        for key, value in filtered_updates.items():
            set_clauses.append(f"{key} = %s")
            params.append(json.dumps(value) if key in json_fields else value)
        params.append(scholarship_id)
        query = f"UPDATE scholarships SET {', '.join(set_clauses)} WHERE id = %s"
        rows = await self.execute_write(query, tuple(params))
        logger.info("scholarship_updated", scholarship_id=scholarship_id, fields=list(filtered_updates.keys()))
        return rows

    async def deactivate_scholarship(self, scholarship_id: str) -> int:
        """Mark a scholarship as inactive (soft delete)."""
        query = "UPDATE scholarships SET is_active = FALSE WHERE id = %s"
        return await self.execute_write(query, (scholarship_id,))

    async def get_all_active(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Return all active scholarships."""
        query = "SELECT * FROM scholarships WHERE is_active = TRUE ORDER BY name LIMIT %s"
        return await self.execute_query(query, (limit,))
