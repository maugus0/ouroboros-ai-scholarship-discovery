"""Scrapy spider for crawling university financial aid and scholarship pages."""

import scrapy

from app.crawlers.parsers.html_parser import scholarship_page_metadata


class UniversityFundingSpider(scrapy.Spider):
    """Crawl university financial aid pages for scholarship information."""

    name = "university_funding_spider"

    def __init__(self, *args, **kwargs):
        urls = kwargs.pop("urls", None)
        super().__init__(*args, **kwargs)
        if urls:
            self.start_urls = urls if isinstance(urls, list) else [urls]

    def parse(self, response):
        """Extract scholarship metadata from a university funding page."""
        yield scholarship_page_metadata(response.text, response.url, html_length=len(response.text))
