"""Crawl job management and execution."""

from typing import Any

from app.core.logging import get_logger
from app.crawlers.on_demand_crawler import crawl_scholarship_page, discover_scholarship_links
from app.repositories.mysql_crawl_job_repo import CrawlJobRepository
from app.services.scholarship_service import ScholarshipService
from app.utils.helpers import get_current_time_iso

logger = get_logger(__name__)


class CrawlService:
    """Manage crawl jobs and execute on-demand crawling."""

    def __init__(self):
        self.crawl_job_repo = CrawlJobRepository()
        self.scholarship_service = ScholarshipService()

    async def create_job(self, data: dict[str, Any]) -> str:
        """Create a new crawl job record."""
        job_id = await self.crawl_job_repo.create_job(data)
        return job_id

    async def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get current status of a crawl job."""
        return await self.crawl_job_repo.get_by_id(job_id)

    async def list_jobs(self, limit: int = 20, offset: int = 0, status: str | None = None) -> list[dict[str, Any]]:
        """List crawl jobs with optional status filter."""
        return await self.crawl_job_repo.list_jobs(limit=limit, offset=offset, status=status)

    async def execute_on_demand_crawl(self, job_id: str, target_url: str) -> None:
        """Execute an on-demand crawl for a specific URL."""
        await self.crawl_job_repo.update_status(job_id, "running")
        scholarships_crawled = 0
        scholarships_updated = 0

        try:
            metadata = await crawl_scholarship_page(target_url)
            if metadata:
                metadata["crawled_at"] = get_current_time_iso()
                await self.scholarship_service.store_crawled_scholarship(metadata)
                scholarships_crawled = 1
                scholarships_updated = 1

            await self.crawl_job_repo.update_status(
                job_id,
                "completed",
                scholarships_crawled=scholarships_crawled,
                scholarships_updated=scholarships_updated,
            )
            logger.info("on_demand_crawl_completed", job_id=job_id, url=target_url)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("on_demand_crawl_failed", job_id=job_id, error=str(exc))
            await self.crawl_job_repo.update_status(job_id, "failed", error_message=str(exc))

    async def execute_source_crawl(self, job_id: str, source_url: str) -> None:
        """Crawl all scholarships from a specific source page."""
        await self.crawl_job_repo.update_status(job_id, "running")
        scholarships_crawled = 0
        scholarships_updated = 0

        try:
            links = await discover_scholarship_links(source_url)

            for link in links:
                try:
                    metadata = await crawl_scholarship_page(link)
                    if metadata:
                        metadata["crawled_at"] = get_current_time_iso()
                        await self.scholarship_service.store_crawled_scholarship(metadata)
                        scholarships_crawled += 1
                        scholarships_updated += 1
                except Exception as link_exc:  # pylint: disable=broad-exception-caught
                    logger.warning("scholarship_page_crawl_failed", url=link, error=str(link_exc))

            await self.crawl_job_repo.update_status(
                job_id,
                "completed",
                scholarships_crawled=scholarships_crawled,
                scholarships_updated=scholarships_updated,
            )
            logger.info("source_crawl_completed", job_id=job_id, scholarships=scholarships_crawled)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("source_crawl_failed", job_id=job_id, error=str(exc))
            await self.crawl_job_repo.update_status(job_id, "failed", error_message=str(exc))
