"""Application configuration loaded from environment variables."""

import json
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.1.0"


class Settings(BaseSettings):
    """All application settings. Loaded from .env file."""

    # ========== Database ==========
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "ouroboros_scholarship_db"
    DB_USERNAME: str = "root"
    DB_PASSWORD: str = ""

    DB_POOL_SIZE: int = 10
    DB_POOL_NAME: str = "scholarship_discovery_pool"
    DB_CONNECTION_TIMEOUT: int = 20

    # ========== Inter-Service Auth ==========
    INTERNAL_TOKEN_VERIFY_ENABLED: bool = False
    INTERNAL_TOKEN_SIGNING_ALGORITHM: str = "RS256"
    INTERNAL_TOKEN_PUBLIC_KEY: str = ""
    INTERNAL_TOKEN_PUBLIC_KEYS: str = "{}"
    INTERNAL_TOKEN_JWKS_URL: str = ""
    INTERNAL_TOKEN_JWKS_REFRESH_SECONDS: int = 60
    INTERNAL_TOKEN_JWKS_TIMEOUT_SECONDS: int = 2
    INTERNAL_TOKEN_AUDIENCE: str = "ouroboros.scholarship-discovery"
    INTERNAL_TOKEN_ISSUER: str = "ouroboros-orchestrator-internal"

    # ========== LLM Configuration ==========
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.1

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 2000

    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_DELAY: int = 2

    # ========== Crawling Configuration ==========
    SCRAPY_CONCURRENT_REQUESTS: int = 8
    SCRAPY_DOWNLOAD_DELAY: float = 2.0
    SCRAPY_USER_AGENT_ROTATION: bool = True
    MIN_CRAWL_DELAY_SECONDS: int = 2
    MAX_CRAWL_DELAY_SECONDS: int = 5
    RESPECT_ROBOTS_TXT: bool = True

    SCHOLARSHIP_STALENESS_DAYS: int = 30
    BATCH_CRAWL_CRON: str = "0 3 * * 0"
    BATCH_CRAWL_SOURCES: str = ""

    # ========== 4-Dimension Linking Weights (must sum to 100) ==========
    LINKING_WEIGHT_UNIVERSITY: int = 50
    LINKING_WEIGHT_FIELD: int = 30
    LINKING_WEIGHT_DEGREE: int = 15
    LINKING_WEIGHT_GEOGRAPHIC: int = 5

    # ========== Confidence Score Thresholds ==========
    MIN_LINK_CONFIDENCE_SCORE: float = 0.40

    # ========== Application ==========
    LOG_LEVEL: str = "INFO"
    USE_MOCK_DATA: bool = True
    ALLOW_DB_FAILURE: bool = False

    # ========== Docker ==========
    RUN_STARTUP_SCRIPTS: bool = True
    DOCKER_MYSQL_PORT: int = 3310

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    def get_db_host(self) -> str:
        return os.getenv("MYSQL_HOST", self.DB_HOST)

    def get_db_name(self) -> str:
        return os.getenv("MYSQL_DATABASE", self.DB_NAME)

    def get_db_user(self) -> str:
        return os.getenv("MYSQL_USER", self.DB_USERNAME)

    def get_db_password(self) -> str:
        return os.getenv("MYSQL_PASSWORD", self.DB_PASSWORD)

    def get_db_port(self) -> int:
        val = os.getenv("MYSQL_PORT")
        return int(val) if val is not None else self.DB_PORT

    def get_linking_weights(self) -> dict[str, int]:
        return {
            "university": self.LINKING_WEIGHT_UNIVERSITY,
            "field": self.LINKING_WEIGHT_FIELD,
            "degree": self.LINKING_WEIGHT_DEGREE,
            "geographic": self.LINKING_WEIGHT_GEOGRAPHIC,
        }

    def get_batch_crawl_sources(self) -> list[str]:
        """Return configured scholarship source listing URLs for scheduled incremental crawls."""
        raw = os.getenv("BATCH_CRAWL_SOURCES", self.BATCH_CRAWL_SOURCES)
        return [item.strip() for item in raw.split(",") if item.strip()]

    def get_internal_token_public_keys(self) -> dict[str, str]:
        """Parse INTERNAL_TOKEN_PUBLIC_KEYS JSON string into a kid->PEM dict."""
        try:
            parsed = json.loads(self.INTERNAL_TOKEN_PUBLIC_KEYS)
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {
            str(kid).strip(): str(pem).strip()
            for kid, pem in parsed.items()
            if kid is not None and str(kid).strip() and pem is not None and str(pem).strip()
        }


settings = Settings()
