"""Scrapy middlewares for user-agent rotation and retry logic."""

import random

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware as BaseRetryMiddleware

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0 Safari/537.36",
]


class RotateUserAgentMiddleware:
    """Downloader middleware that rotates user agents on each request."""

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def process_request(self, request, spider):  # pylint: disable=unused-argument
        request.headers["User-Agent"] = random.choice(USER_AGENTS)

    def spider_opened(self, spider):
        spider.logger.info("RotateUserAgentMiddleware enabled for %s", spider.name)


class RetryMiddleware(BaseRetryMiddleware):
    """Extended retry middleware with logging."""

    def _retry(self, request, reason, spider):
        spider.logger.warning("Retrying %s (reason: %s)", request.url, reason)
        return super()._retry(request, reason, spider)
