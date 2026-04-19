"""Scrapy pipelines for data validation and database storage."""

import asyncio

from scrapy.exceptions import DropItem
from scrapy.utils.defer import deferred_from_coro

from app.core.logging import get_logger
from app.services.crawl_service import CrawlService

logger = get_logger(__name__)


class ValidateScholarshipPipeline:
    """Validate that scraped items have the minimum required fields."""

    REQUIRED_FIELDS = ["name", "source_url"]

    def process_item(self, item, spider):  # pylint: disable=unused-argument
        for field in self.REQUIRED_FIELDS:
            if not item.get(field):
                raise DropItem(f"Missing required field: {field}")

        if item.get("funding_amount") is not None:
            try:
                item["funding_amount"] = float(item["funding_amount"])
            except (ValueError, TypeError):
                item["funding_amount"] = None

        return item


class StoreScholarshipPipeline:
    """Store validated scholarship items (placeholder for async DB writes).

    In production, this pipeline queues items for batch insertion.
    The actual DB write happens in the crawl service after the spider completes.
    """

    def __init__(self):
        self.items: list[dict] = []
        self.crawl_service = CrawlService()

    def process_item(self, item, spider):
        self.items.append(dict(item))
        logger.info("scholarship_item_queued", scholarship_name=item.get("name"))
        return item

    def close_spider(self, spider):
        logger.info("spider_closed_processing", spider=spider.name, items_queued=len(self.items))
        if not self.items:
            return

        active_programs = spider.settings.get("ACTIVE_PROGRAMS", [])

        async def process_all():
            semaphore = asyncio.Semaphore(5)

            async def process(item):
                async with semaphore:
                    try:
                        await self.crawl_service._process_scraped_item(item, active_programs)
                    except Exception as e:
                        logger.error(
                            "pipeline_processing_failed",
                            error=str(e),
                            source_url=item.get("source_url"),
                            spider=spider.name,
                        )

            await asyncio.gather(*(process(item) for item in self.items))

        return deferred_from_coro(process_all())
