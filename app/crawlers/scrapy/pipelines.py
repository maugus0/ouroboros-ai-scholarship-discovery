"""Scrapy pipelines for data validation and database storage."""

from scrapy.exceptions import DropItem

from app.core.logging import get_logger

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

    def process_item(self, item, spider):  # pylint: disable=unused-argument
        self.items.append(dict(item))
        logger.info("scholarship_item_queued", scholarship_name=item.get("name"))
        return item

    def close_spider(self, spider):
        logger.info("spider_closed", spider=spider.name, items_queued=len(self.items))
