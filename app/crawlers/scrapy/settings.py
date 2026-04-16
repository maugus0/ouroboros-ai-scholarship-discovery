"""Scrapy project settings for the Scholarship Discovery Agent."""

from app.config import settings

BOT_NAME = "scholarship_discovery"
SPIDER_MODULES = ["app.crawlers.scrapy.spiders"]
NEWSPIDER_MODULE = "app.crawlers.scrapy.spiders"

ROBOTSTXT_OBEY = settings.RESPECT_ROBOTS_TXT

CONCURRENT_REQUESTS = settings.SCRAPY_CONCURRENT_REQUESTS
DOWNLOAD_DELAY = settings.SCRAPY_DOWNLOAD_DELAY
RANDOMIZE_DOWNLOAD_DELAY = True

CONCURRENT_REQUESTS_PER_DOMAIN = 4
# CONCURRENT_REQUESTS_PER_IP = 4

COOKIES_ENABLED = False

DOWNLOADER_MIDDLEWARES = {
    "app.crawlers.scrapy.middlewares.RotateUserAgentMiddleware": 400,
    "app.crawlers.scrapy.middlewares.RetryMiddleware": 550,
}

ITEM_PIPELINES = {
    "app.crawlers.scrapy.pipelines.ValidateScholarshipPipeline": 300,
    "app.crawlers.scrapy.pipelines.StoreScholarshipPipeline": 400,
}

RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
