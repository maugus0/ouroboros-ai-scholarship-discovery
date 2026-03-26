"""Scrapy spider for batch-crawling scholarship database listing pages."""

import scrapy

from app.crawlers.parsers.html_parser import extract_links


class ScholarshipSpider(scrapy.Spider):
    """Crawl scholarship database sites and extract links to individual pages."""

    name = "scholarship_spider"
    allowed_domains: list[str] = []

    def __init__(self, start_urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if start_urls:
            self.start_urls = start_urls if isinstance(start_urls, list) else [start_urls]

    def parse(self, response, **kwargs):
        """Extract scholarship links from a listing page."""
        scholarship_links = extract_links(response.text, response.url)
        self.logger.info("Found %d scholarship links on %s", len(scholarship_links), response.url)

        for link in scholarship_links:
            yield scrapy.Request(url=link, callback=self.parse_scholarship_page)

    def parse_scholarship_page(self, response):
        """Extract basic metadata from an individual scholarship page."""
        from app.crawlers.parsers.html_parser import extract_basic_metadata

        metadata = extract_basic_metadata(response.text)
        metadata["source_url"] = response.url

        yield metadata
