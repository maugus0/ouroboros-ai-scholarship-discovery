"""Tests for application configuration."""

import os


def test_settings_load():
    os.environ.setdefault("ALLOW_DB_FAILURE", "true")
    os.environ.setdefault("X_SERVICE_TOKEN", "test-service-token")

    from app.config import settings

    assert settings.DB_NAME == "ouroboros_scholarship_db"
    assert settings.DB_PORT == 3306
    assert settings.DB_POOL_NAME == "scholarship_discovery_pool"


def test_settings_db_helpers():
    os.environ.setdefault("ALLOW_DB_FAILURE", "true")
    os.environ.setdefault("X_SERVICE_TOKEN", "test-service-token")

    from app.config import settings

    assert isinstance(settings.get_db_host(), str)
    assert isinstance(settings.get_db_port(), int)
    assert isinstance(settings.get_db_name(), str)
    assert isinstance(settings.get_db_user(), str)


def test_linking_weights():
    from app.config import settings

    weights = settings.get_linking_weights()
    assert isinstance(weights, dict)
    assert sum(weights.values()) == 100
    assert "university" in weights
    assert "field" in weights
    assert "degree" in weights
    assert "geographic" in weights


def test_crawl_settings():
    from app.config import settings

    assert settings.SCRAPY_DOWNLOAD_DELAY >= 1.0
    assert settings.SCHOLARSHIP_STALENESS_DAYS > 0
    assert settings.RESPECT_ROBOTS_TXT is True


def test_confidence_threshold():
    from app.config import settings

    assert 0.0 <= settings.MIN_LINK_CONFIDENCE_SCORE <= 1.0
