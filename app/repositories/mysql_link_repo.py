"""Data-access layer for the scholarship_program_links table (raw SQL, aiomysql)."""

import json
from typing import Any

from app.core.logging import get_logger
from app.repositories.mysql_base import MySQLBaseRepository
from app.utils.helpers import generate_uuid

logger = get_logger(__name__)


class LinkRepository(MySQLBaseRepository):
    """CRUD operations on the ``scholarship_program_links`` table."""

    async def create_or_update(
        self,
        scholarship_id: str,
        program_id: str,
        link_type: str,
        confidence_score: float,
        match_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Insert or update a scholarship-program link. Returns the link record."""
        link_id = generate_uuid()
        metadata_json = json.dumps(match_metadata) if match_metadata else None
        query = """
            INSERT INTO scholarship_program_links (
                id, scholarship_id, program_id, link_type, confidence_score, match_metadata
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                link_type = VALUES(link_type),
                confidence_score = VALUES(confidence_score),
                match_metadata = VALUES(match_metadata)
        """
        params = (link_id, scholarship_id, program_id, link_type, confidence_score, metadata_json)
        await self.execute_write(query, params)
        logger.info(
            "link_created_or_updated",
            scholarship_id=scholarship_id,
            program_id=program_id,
            confidence=confidence_score,
        )
        return {
            "id": link_id,
            "scholarship_id": scholarship_id,
            "program_id": program_id,
            "link_type": link_type,
            "confidence_score": confidence_score,
            "match_metadata": match_metadata,
        }

    async def get_scholarship_ids_for_programs(
        self,
        program_ids: list[str],
        min_confidence: float = 0.0,
    ) -> list[str]:
        """Distinct scholarship IDs linked to any of the given programs.

        Used by ``ScholarshipService.search`` when ``program_ids`` is set on the API request.
        """
        if not program_ids:
            return []
        placeholders = ", ".join(["%s"] * len(program_ids))
        query = f"""
            SELECT DISTINCT scholarship_id FROM scholarship_program_links
            WHERE program_id IN ({placeholders}) AND confidence_score >= %s
        """  # nosec B608
        params = tuple(program_ids) + (min_confidence,)
        rows = await self.execute_query(query, params)
        return [row["scholarship_id"] for row in rows]

    async def get_by_program_id(
        self,
        program_id: str,
        min_confidence: float = 0.0,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return links for a specific program, filtered by minimum confidence.

        When ``limit`` is provided, pagination is applied at the DB level.
        """
        if limit is not None:
            query = """
                SELECT * FROM scholarship_program_links
                WHERE program_id = %s AND confidence_score >= %s
                ORDER BY confidence_score DESC
                LIMIT %s OFFSET %s
            """
            return await self.execute_query(query, (program_id, min_confidence, limit, offset))

        query = """
            SELECT * FROM scholarship_program_links
            WHERE program_id = %s AND confidence_score >= %s
            ORDER BY confidence_score DESC
        """
        return await self.execute_query(query, (program_id, min_confidence))

    async def count_by_program_id(self, program_id: str, min_confidence: float = 0.0) -> int:
        """Count links for a specific program above minimum confidence."""
        query = """
            SELECT COUNT(*) AS total FROM scholarship_program_links
            WHERE program_id = %s AND confidence_score >= %s
        """
        result = await self.execute_one(query, (program_id, min_confidence))
        return result["total"] if result else 0

    async def get_by_scholarship_id(self, scholarship_id: str) -> list[dict[str, Any]]:
        """Return all links for a specific scholarship."""
        query = """
            SELECT * FROM scholarship_program_links
            WHERE scholarship_id = %s
            ORDER BY confidence_score DESC
        """
        return await self.execute_query(query, (scholarship_id,))

    async def delete_by_scholarship_id(self, scholarship_id: str) -> int:
        """Delete all links for a scholarship."""
        query = "DELETE FROM scholarship_program_links WHERE scholarship_id = %s"
        rows = await self.execute_write(query, (scholarship_id,))
        logger.info("links_deleted", scholarship_id=scholarship_id, count=rows)
        return rows

    async def count_links(self, min_confidence: float = 0.0) -> int:
        """Count total links above minimum confidence."""
        query = "SELECT COUNT(*) AS total FROM scholarship_program_links WHERE confidence_score >= %s"
        result = await self.execute_one(query, (min_confidence,))
        return result["total"] if result else 0
