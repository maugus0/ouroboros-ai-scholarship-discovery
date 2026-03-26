"""Tests for HTML parsing utilities."""

from app.crawlers.parsers.html_parser import (
    _extract_deadline,
    _extract_funding_amount,
    extract_basic_metadata,
    extract_page_text,
)


def test_extract_page_text_removes_scripts():
    html = "<html><body><script>var x=1;</script><p>Hello World</p></body></html>"
    text = extract_page_text(html)
    assert "var x" not in text
    assert "Hello World" in text


def test_extract_page_text_removes_nav():
    html = "<html><body><nav>Menu</nav><main>Content</main></body></html>"
    text = extract_page_text(html)
    assert "Menu" not in text
    assert "Content" in text


def test_extract_basic_metadata_title():
    html = "<html><head><title>DAAD Scholarship</title></head><body><h1>DAAD Full Scholarship</h1></body></html>"
    metadata = extract_basic_metadata(html)
    assert metadata["name"] == "DAAD Full Scholarship"


def test_extract_deadline_iso():
    assert _extract_deadline("Application deadline: 2026-12-15") == "2026-12-15"


def test_extract_deadline_none():
    assert _extract_deadline("No deadline mentioned here") is None


def test_extract_funding_amount():
    result = _extract_funding_amount("Award value: $50,000 per year")
    assert result == 50000.0


def test_extract_funding_amount_none():
    assert _extract_funding_amount("Contact us for funding details") is None
