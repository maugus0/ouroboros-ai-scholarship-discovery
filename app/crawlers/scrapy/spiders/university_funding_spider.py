"""Scrapy spider for crawling university financial aid and scholarship pages."""

import scrapy

from app.crawlers.parsers.html_parser import extract_basic_metadata


class UniversityFundingSpider(scrapy.Spider):
    """Crawl university financial aid pages for scholarship information."""

    name = "university_funding_spider"

    def __init__(self, urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if urls:
            self.start_urls = urls if isinstance(urls, list) else [urls]

    def parse(self, response, **kwargs):
        """Extract scholarship metadata from a university funding page."""
        metadata = extract_basic_metadata(response.text)
        metadata["source_url"] = response.url
        metadata["html_length"] = len(response.text)

        yield metadata
