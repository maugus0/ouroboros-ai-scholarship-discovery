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

    async def get_by_program_id(
        self,
        program_id: str,
        min_confidence: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Return all links for a specific program, filtered by minimum confidence."""
        query = """
            SELECT * FROM scholarship_program_links
            WHERE program_id = %s AND confidence_score >= %s
            ORDER BY confidence_score DESC
        """
        return await self.execute_query(query, (program_id, min_confidence))

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
