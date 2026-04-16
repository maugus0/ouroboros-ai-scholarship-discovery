from __future__ import annotations

"""APScheduler-based periodic crawl scheduling."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.core.logging import get_logger
from app.services.crawl_service import CrawlService
from app.services.program_service import ProgramService

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Return the global scheduler instance."""
    global _scheduler  # pylint: disable=global-statement
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def start_scheduler() -> None:
    """Start the batch crawl scheduler."""
    scheduler = get_scheduler()

    cron_parts = settings.BATCH_CRAWL_CRON.split()
    if len(cron_parts) == 5:
        minute, hour, day, month, day_of_week = cron_parts
        scheduler.add_job(
            _batch_crawl_trigger,
            "cron",
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            id="batch_crawl",
            replace_existing=True,
        )
        logger.info("batch_crawl_scheduled", cron=settings.BATCH_CRAWL_CRON)

    if not scheduler.running:
        scheduler.start()
        logger.info("scheduler_started")


async def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    global _scheduler  # pylint: disable=global-statement
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler_stopped")


async def _batch_crawl_trigger() -> None:
    """Run scheduled incremental crawls for each configured scholarship source."""
    logger.info("batch_crawl_triggered")

    source_urls = settings.get_batch_crawl_sources()
    if not source_urls:
        logger.warning("batch_crawl_skipped_no_sources_configured")
        return

    crawl_service = CrawlService()
    program_service = ProgramService()
    active_programs = await program_service.get_all_active()

    for source_url in source_urls:
        job_id = await crawl_service.create_job(
            {
                "job_type": "batch",
                "target_source": source_url,
            }
        )

        try:
            await crawl_service.execute_source_crawl(job_id, source_url, active_programs)
            logger.info("batch_crawl_job_completed", job_id=job_id, source_url=source_url)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("batch_crawl_job_failed", job_id=job_id, source_url=source_url, error=str(exc))
