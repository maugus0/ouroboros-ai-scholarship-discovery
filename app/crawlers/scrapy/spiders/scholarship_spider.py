"""Scrapy spider for batch-crawling scholarship database listing pages.

Follows the same ``kwargs.pop('start_urls')`` pattern as Program Discovery ``UniversitySpider``.
"""

import scrapy

from app.crawlers.parsers.html_parser import extract_links, scholarship_page_metadata


class ScholarshipSpider(scrapy.Spider):
    """Crawl scholarship database sites and extract links to individual pages."""

    name = "scholarship_spider"
    allowed_domains: list[str] = []

    def __init__(self, *args, **kwargs):
        start_urls = kwargs.pop("start_urls", None)
        super().__init__(*args, **kwargs)
        if start_urls:
            self.start_urls = start_urls if isinstance(start_urls, list) else [start_urls]

    def parse(self, response):
        """Extract scholarship links from a listing page."""
        scholarship_links = extract_links(response.text, response.url)
        self.logger.info("Found %d scholarship links on %s", len(scholarship_links), response.url)

        for link in scholarship_links:
            yield scrapy.Request(url=link, callback=self.parse_scholarship_page)

    def parse_scholarship_page(self, response):
        """Extract basic metadata from an individual scholarship page."""
        referer = response.request.headers.get("Referer", b"").decode("utf-8", errors="ignore")
        yield scholarship_page_metadata(response.text, response.url, university_url=referer)
