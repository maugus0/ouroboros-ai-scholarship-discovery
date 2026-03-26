"""Scholarship search, filter, and storage orchestration."""

from typing import Any

from app.config import settings
from app.core.logging import get_logger
from app.repositories.mysql_link_repo import LinkRepository
from app.repositories.mysql_scholarship_repo import ScholarshipRepository

logger = get_logger(__name__)


class ScholarshipService:
    """Business logic for scholarship search and discovery."""

    def __init__(self):
        self.scholarship_repo = ScholarshipRepository()
        self.link_repo = LinkRepository()

    async def search(
        self,
        provider: str | None = None,
        program_ids: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search scholarships with optional filters."""
        scholarship_ids: list[str] | None = None
        if program_ids:
            scholarship_ids = await self.link_repo.get_scholarship_ids_for_programs(program_ids)

        scholarships = await self.scholarship_repo.search_scholarships(
            provider=provider,
            scholarship_ids=scholarship_ids,
            limit=limit,
            offset=offset,
        )

        total = await self.scholarship_repo.count_scholarships(
            provider=provider,
            scholarship_ids=scholarship_ids,
        )

        return {
            "scholarships": scholarships,
            "total": total,
        }

    async def get_scholarship_detail(self, scholarship_id: str) -> dict[str, Any] | None:
        """Return full scholarship details."""
        scholarship = await self.scholarship_repo.get_by_id(scholarship_id)
        if not scholarship:
            return None
        return scholarship

    async def get_stale_scholarships(self) -> list[dict[str, Any]]:
        """Return scholarships not crawled within the staleness threshold."""
        return await self.scholarship_repo.get_stale_scholarships(settings.SCHOLARSHIP_STALENESS_DAYS)

    async def store_crawled_scholarship(self, data: dict[str, Any]) -> str:
        """Store or update a crawled scholarship."""
        existing = await self.scholarship_repo.search_scholarships(limit=100)
        for s in existing:
            if s.get("source_url") == data.get("source_url"):
                await self.scholarship_repo.update_scholarship(s["id"], data)
                logger.info("scholarship_updated_from_crawl", scholarship_id=s["id"])
                return s["id"]

        scholarship_id = await self.scholarship_repo.create_scholarship(data)
        logger.info("scholarship_created_from_crawl", scholarship_id=scholarship_id)
        return scholarship_id

    async def get_all_active(self) -> list[dict[str, Any]]:
        """Return all active scholarships."""
        return await self.scholarship_repo.get_all_active()
