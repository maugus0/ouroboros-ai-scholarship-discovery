"""Data-access layer for the crawl_jobs table (raw SQL, aiomysql)."""

from typing import Any

from app.core.logging import get_logger
from app.repositories.mysql_base import MySQLBaseRepository
from app.utils.helpers import generate_uuid

logger = get_logger(__name__)


class CrawlJobRepository(MySQLBaseRepository):
    """CRUD operations on the ``crawl_jobs`` table."""

    async def create_job(self, data: dict[str, Any]) -> str:
        """Insert a new crawl job and return its UUID."""
        job_id = generate_uuid()
        query = """
            INSERT INTO crawl_jobs (
                id, job_type, target_url, target_source, status
            ) VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            job_id,
            data["job_type"],
            data.get("target_url"),
            data.get("target_source"),
            "pending",
        )
        await self.execute_write(query, params)
        logger.info("crawl_job_created", job_id=job_id, job_type=data["job_type"])
        return job_id

    async def get_by_id(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a crawl job by UUID."""
        query = "SELECT * FROM crawl_jobs WHERE id = %s"
        return await self.execute_one(query, (job_id,))

    async def update_status(
        self,
        job_id: str,
        status: str,
        error_message: str | None = None,
        scholarships_crawled: int | None = None,
        scholarships_updated: int | None = None,
    ) -> int:
        """Update the status and metrics of a crawl job."""
        set_parts = ["status = %s"]
        params: list[Any] = [status]

        if status == "running":
            set_parts.append("started_at = NOW()")
        elif status in ("completed", "failed"):
            set_parts.append("completed_at = NOW()")

        if error_message is not None:
            set_parts.append("error_message = %s")
            params.append(error_message)

        if scholarships_crawled is not None:
            set_parts.append("scholarships_crawled = %s")
            params.append(scholarships_crawled)

        if scholarships_updated is not None:
            set_parts.append("scholarships_updated = %s")
            params.append(scholarships_updated)

        params.append(job_id)
        query = f"UPDATE crawl_jobs SET {', '.join(set_parts)} WHERE id = %s"
        rows = await self.execute_write(query, tuple(params))
        logger.info("crawl_job_updated", job_id=job_id, status=status)
        return rows

    async def list_jobs(self, limit: int = 20, offset: int = 0, status: str | None = None) -> list[dict[str, Any]]:
        """Return a paginated list of crawl jobs."""
        if status:
            query = "SELECT * FROM crawl_jobs WHERE status = %s ORDER BY created_at DESC LIMIT %s OFFSET %s"
            return await self.execute_query(query, (status, limit, offset))
        query = "SELECT * FROM crawl_jobs ORDER BY created_at DESC LIMIT %s OFFSET %s"
        return await self.execute_query(query, (limit, offset))

    async def get_running_jobs_count(self) -> int:
        """Return the number of currently running crawl jobs."""
        result = await self.execute_one("SELECT COUNT(*) AS total FROM crawl_jobs WHERE status = 'running'")
        return result["total"] if result else 0
