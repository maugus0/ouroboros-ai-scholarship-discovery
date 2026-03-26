"""Tests for HTML/URL utility functions."""

from app.utils.html_utils import clean_html_text, extract_domain, is_valid_url, truncate_text


def test_is_valid_url_https():
    assert is_valid_url("https://www.csc.edu.cn/scholarships") is True


def test_is_valid_url_http():
    assert is_valid_url("http://example.com") is True


def test_is_valid_url_invalid():
    assert is_valid_url("not-a-url") is False
    assert is_valid_url("") is False
    assert is_valid_url("ftp://files.example.com") is False


def test_extract_domain():
    assert extract_domain("https://www.mit.edu/scholarships") == "mit.edu"
    assert extract_domain("https://csc.edu.cn/path") == "csc.edu.cn"


def test_clean_html_text():
    text = "   Hello    World   \n\n\n\n  Test  "
    cleaned = clean_html_text(text)
    assert "  " not in cleaned or cleaned == "Hello World Test"


def test_truncate_text_short():
    text = "Short text"
    assert truncate_text(text, max_length=100) == text


def test_truncate_text_long():
    text = "word " * 5000
    result = truncate_text(text, max_length=100)
    assert len(result) <= 105
    assert result.endswith("...")
