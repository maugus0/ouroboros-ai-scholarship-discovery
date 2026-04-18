"""Tests for the sample Chevening and DAAD spiders using mock HTML and JS pages."""

from scrapy.http import HtmlResponse, Request, TextResponse

from app.crawlers.scrapy.spiders.chevening_spider import CheveningSpider
from app.crawlers.scrapy.spiders.daad_spider import DAADSpider


def _html_response(url: str, body: str) -> HtmlResponse:
    request = Request(url=url)
    return HtmlResponse(url=url, request=request, body=body.encode("utf-8"), encoding="utf-8")


def _text_response(url: str, body: str) -> TextResponse:
    request = Request(url=url)
    return TextResponse(url=url, request=request, body=body.encode("utf-8"), encoding="utf-8")


def test_chevening_spider_extracts_standard_scholarship_seed():
    spider = CheveningSpider()
    response = _html_response(
        "https://www.chevening.org/scholarships/who-can-apply/",
        """
        <html>
          <body>
            <main>
              <h1>Who can apply</h1>
              <h2>Eligibility</h2>
              <p>Applicants must return to their home country for at least two years.</p>
              <p>Applicants need an undergraduate degree and work experience.</p>
            </main>
          </body>
        </html>
        """,
    )

    results = list(spider.parse_masters_base(response))

    assert len(results) == 1
    assert results[0].url == "https://www.chevening.org/scholarships/apply/"
    assert results[0].meta["scholarship_seed"]["name"] == "Chevening Master's Scholarship (Global)"
    assert "home country" in results[0].meta["scholarship_seed"]["eligibility_text"]
    assert results[0].meta["scholarship_seed"]["application_requirements"]["country_application_statuses"] == []


def test_chevening_spider_extracts_country_application_statuses():
    spider = CheveningSpider()
    request = Request(
        url="https://www.chevening.org/scholarships/apply/",
        meta={
            "scholarship_seed": {
                "name": "Chevening Master's Scholarship (Global)",
                "provider": "UK Government (Chevening)",
                "source_url": "https://www.chevening.org/scholarships/",
                "description": "seed",
                "funding_amount": None,
                "currency": "GBP",
                "deadline": None,
                "eligibility_text": "seed eligibility",
                "application_requirements": {
                    "application_route_url": "https://www.chevening.org/scholarships/apply/",
                    "country_application_statuses": [],
                },
                "spider_name": spider.name,
            }
        },
    )
    response = HtmlResponse(
        url=request.url,
        request=request,
        body="""
        <html>
          <body>
            <main>
              <select>
                <option value="">Choose a country</option>
                <option value="/scholarships/apply/nigeria/">Nigeria - applications open</option>
                <option value="/scholarships/apply/brazil/">Brazil - applications closed</option>
              </select>
            </main>
          </body>
        </html>
        """.encode("utf-8"),
        encoding="utf-8",
    )

    items = list(spider.parse_masters_apply(response))
    item = items[0]

    assert item["name"] == "Chevening Master's Scholarship (Global)"
    assert item["currency"] == "GBP"
    statuses = item["application_requirements"]["country_application_statuses"]
    assert statuses[0]["country"] == "Nigeria"
    assert statuses[0]["status"] == "open"
    assert statuses[1]["country"] == "Brazil"
    assert statuses[1]["status"] == "closed"


def test_chevening_spider_extracts_fellowship_links():
    spider = CheveningSpider()
    response = _html_response(
        "https://www.chevening.org/fellowships/find-a-programme/",
        """
        <html>
          <body>
            <main>
              <a href="/fellowships/example-award/">Example</a>
              <a href="/fellowships/find-a-programme/">Listing</a>
            </main>
          </body>
        </html>
        """,
    )

    results = list(spider.parse_fellowships_list(response))

    assert len(results) == 1
    assert results[0].url == "https://www.chevening.org/fellowships/example-award/"


def test_chevening_spider_extracts_fellowship_metadata():
    spider = CheveningSpider()
    response = _html_response(
        "https://www.chevening.org/fellowships/example-award/",
        """
        <html>
          <body>
            <main>
              <h1>Chevening Science Fellowship</h1>
              <p>Funding available: GBP 18,000 per year</p>
              <p>Deadline: November 5 2026</p>
              <h2>Eligibility</h2>
              <p>Applicants must be citizens of eligible countries and hold an undergraduate degree.</p>
            </main>
          </body>
        </html>
        """,
    )

    items = list(spider.parse_fellowship_detail(response))
    item = items[0]

    assert item["name"] == "Chevening Science Fellowship"
    assert item["provider"] == "UK Government (Chevening)"
    assert item["funding_amount"] == 18000.0
    assert item["deadline"] == "November 5 2026"
    assert "eligible countries" in item["eligibility_text"]


def test_daad_spider_extracts_detail_requests_from_js_feed():
    spider = DAADSpider()
    response = _text_response(
        "https://www.daad.de/bundles/daadstipendiendatenbanklsh/data/a/js/scholarships.js",
        'var scholarships = [{"id":"50015492"},{"id":"50015493"}];',
    )

    results = list(spider.parse(response))
    urls = {request.url for request in results}

    assert (
        "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/?detail=50015492" in urls
    )
    assert (
        "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/?detail=50015493" in urls
    )


def test_daad_spider_uses_static_js_metadata_without_detail_request():
    spider = DAADSpider()
    response = _text_response(
        "https://www.daad.de/bundles/daadstipendiendatenbanklsh/data/a/js/scholarships.js",
        """
        var scholarships = [{
          "id":"50015492",
          "title":"DAAD Research Grant",
          "description":"Research funding for outstanding postgraduate applicants.",
          "deadline":"October 31 2026",
          "eligibility":"Open to postgraduate students in engineering."
        }];
        """,
    )

    results = list(spider.parse(response))

    assert len(results) == 1
    item = results[0]
    assert item["name"] == "DAAD Research Grant"
    assert item["deadline"] == "October 31 2026"
    assert "postgraduate students" in item["eligibility_text"]


def test_daad_spider_extracts_metadata_from_mock_page():
    spider = DAADSpider()
    response = _html_response(
        "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/?detail=50015492",
        """
        <html>
          <body>
            <h1>DAAD Research Grant</h1>
            <p>Funding: EUR 1,200 monthly stipend for international students.</p>
            <p>Application deadline: October 31 2026</p>
            <h2>Who can apply?</h2>
            <p>Open to postgraduate students in engineering with strong academic records.</p>
            <div>
              <p>This scholarship supports research stays in Germany for outstanding applicants and includes travel support.</p>
              <p>Applicants should demonstrate research alignment and submit references.</p>
            </div>
          </body>
        </html>
        """,
    )

    items = list(spider.parse_scholarship_page(response))
    item = items[0]

    assert item["name"] == "DAAD Research Grant"
    assert item["provider"] == "DAAD"
    assert item["funding_amount"] == 1200.0
    assert item["currency"] == "EUR"
    assert item["deadline"] == "October 31 2026"
    assert "postgraduate students" in item["eligibility_text"]


def test_daad_spider_merges_seed_data_with_detail_page():
    spider = DAADSpider()
    request = Request(
        url="https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/?detail=50015492",
        meta={
            "scholarship_seed": {
                "name": "Seed Title",
                "description": "Seed description",
                "deadline": None,
                "funding_amount": None,
                "eligibility_text": None,
            }
        },
    )
    response = HtmlResponse(
        url=request.url,
        request=request,
        body="""
        <html>
          <body>
            <h1>DAAD Research Grant</h1>
            <p>Funding: EUR 1,200 monthly stipend for international students.</p>
            <p>Application deadline: October 31 2026</p>
            <h2>Who can apply?</h2>
            <p>Open to postgraduate students in engineering with strong academic records.</p>
          </body>
        </html>
        """.encode("utf-8"),
        encoding="utf-8",
    )

    items = list(spider.parse_scholarship_page(response))
    item = items[0]

    assert item["name"] == "DAAD Research Grant"
    assert item["description"]
    assert item["deadline"] == "October 31 2026"


def test_daad_spider_ignores_generic_page_title_on_detail_pages():
    spider = DAADSpider()
    response = _html_response(
        "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/?detail=50015492",
        """
        <html>
          <head>
            <title>Finding Scholarships - DAAD</title>
          </head>
          <body>
            <div class="content">
              <h1>Future Ukraine: Research Grants for Ukrainian Master's students and researchers</h1>
              <h2>Objective</h2>
              <p>Funding of highly qualified Ukrainian graduates for short research stays in Germany.</p>
            </div>
          </body>
        </html>
        """,
    )

    item = list(spider.parse_scholarship_page(response))[0]

    assert item["name"].startswith("Future Ukraine:")
    assert "short research stays in Germany" in item["description"]
