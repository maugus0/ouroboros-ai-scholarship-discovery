# Ouroboros Scholarship Discovery Agent

Scholarship crawling, eligibility filtering, and program-linking service for the **Ouroboros AI** scholarship discovery platform.

---

## Table of Contents

- [Overview](#overview)
- [Comparison with Program Discovery Agent](#comparison-with-program-discovery-agent)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Prompt System](#prompt-system)
- [4-Dimension Linking Algorithm](#4-dimension-linking-algorithm)
- [Eligibility Filtering](#eligibility-filtering)
- [Crawling Strategy](#crawling-strategy)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Attribution](#attribution)

---

## Overview

The Scholarship Discovery Agent is responsible for:

1. **Crawling scholarship databases** and university funding pages using a dual strategy (Scrapy batch + BeautifulSoup on-demand)
2. **Extracting eligibility criteria** via LLM-assisted parsing (OpenAI primary, Anthropic fallback)
3. **Linking scholarships to academic programs** through a 4-dimension confidence scoring system
4. **Filtering scholarships by student eligibility** with strict binary matching against profile data
5. **Serving filtered results** to the Orchestrator via authenticated HTTP endpoints

**Key Design Principles:**

- Single responsibility — crawl, extract, link, filter, serve
- No direct frontend access — only the Orchestrator (port 8000) calls this service
- No ORM overhead — raw SQL with `aiomysql` async connection pool
- Ethical crawling — robots.txt compliance, configurable delays, user-agent rotation
- Decoupled architecture — does NOT call Program Discovery Agent; Orchestrator passes `program_id` via payload
- LLM cost tracking — every API call logged with token counts and cost

---

## Comparison with Program Discovery Agent

Both agents are sibling microservices: same **FastAPI + aiomysql + repository pattern**, **X-Service-Token** auth, **structlog** middleware, **Scrapy + httpx/BeautifulSoup** crawling, **OpenAI → Anthropic** LLM fallback, **APScheduler** batch jobs, **numbered SQL migrations**, and the same **7-job GitHub Actions** shape (`format`, `lint`, `unit-tests`, `type-check`, `integration`, `security`, `Docker build`). Differences are domain, data model, and scoring.

| Topic | Program Discovery (`ouroboros-ai-program-discovery`) | Scholarship Discovery (this repo) |
|-------|------------------------------------------------------|-----------------------------------|
| **HTTP port** | 8002 | 8003 |
| **MySQL database** | `ouroboros_program_db` | `ouroboros_scholarship_db` |
| **Docker MySQL host port** | 3309 | 3310 |
| **Core tables** | `universities`, `programs`, `program_requirements` | `scholarships`, `eligibility_criteria`, `scholarship_program_links` |
| **Shared tables** | `crawl_jobs`, `llm_call_logs` | Same (column names adapted for scholarships) |
| **Primary API surface** | `/api/v1/programs/*` | `/api/v1/scholarships/*` plus `/by-program/{program_id}` and link endpoints |
| **Search filters** | Field, degree, university, ranking pipeline | Optional **provider**; optional **program_ids** (via links table); optional **student_profile** for eligibility |
| **Ranking / scoring** | Multi-factor **program ranking** (field, requirements, university rank, deadline, tuition) | **Scholarship–program linking** confidence (university, field, degree, geography) plus **eligibility** filtering for students |
| **Orchestrator contract** | Search/rank programs for a student | Search/filter scholarships; accept **program metadata in payload** for linking (no direct call to Program Discovery) |
| **Repositories** | University, program, requirement, crawl job, LLM log | Scholarship, eligibility criteria, link, crawl job, LLM log |
| **Staleness & schedule** | `PROGRAM_STALENESS_DAYS`, batch cron `0 2 * * 0` | `SCHOLARSHIP_STALENESS_DAYS`, batch cron `0 3 * * 0` (staggered after programs) |
| **Crawlers** | Listing + program-detail spiders | Scholarship listing + university funding spiders (same pipeline/middleware ideas) |

**Mental model:** Program Discovery owns **canonical program catalog** in its DB. Scholarship Discovery owns **scholarships and links**; `program_id` in `scholarship_program_links` is an **opaque UUID** supplied by the orchestrator (not a foreign key across services).

---

## Architecture

```
┌─────────────────────────────────────┐
│       Frontend (React + Vite)       │
│       (http://localhost:3000)       │
└──────────────┬──────────────────────┘
               │
               │ JWT Bearer Token
               ▼
┌──────────────────────────────────────────────────────┐
│          Orchestrator Service (8000)                  │
│          X-Service-Token                             │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│       Scholarship Discovery Agent (8003)             │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │  API Layer (FastAPI)                        │     │
│  │  POST /api/v1/scholarships/search           │     │
│  │  GET  /api/v1/scholarships/{id}             │     │
│  │  GET  /api/v1/scholarships/by-program/{pid} │     │
│  │  POST /api/v1/scholarships/crawl            │     │
│  │  POST /api/v1/scholarships/link             │     │
│  └─────────────────────┬───────────────────────┘     │
│                        │                             │
│  ┌─────────────────────▼───────────────────────┐     │
│  │  Service Layer                              │     │
│  │  ScholarshipService   (search, store)       │     │
│  │  EligibilityFilter    (profile matching)    │     │
│  │  LinkingService       (4-dim scoring)       │     │
│  │  CrawlService         (job management)      │     │
│  │  LLMService           (OpenAI → Anthropic)  │     │
│  │  SchedulerService     (APScheduler batch)   │     │
│  └─────────────────────┬───────────────────────┘     │
│                        │                             │
│  ┌─────────────────────▼───────────────────────┐     │
│  │  Crawler Layer                              │     │
│  │  Scrapy Spiders    (batch crawling)         │     │
│  │  On-Demand Crawler (httpx + BeautifulSoup)  │     │
│  │  HTML Parser       (BeautifulSoup helpers)  │     │
│  │  LLM Parser        (structured extraction)  │     │
│  └─────────────────────┬───────────────────────┘     │
│                        │                             │
│  ┌─────────────────────▼───────────────────────┐     │
│  │  Repository Layer (Raw SQL / aiomysql)      │     │
│  │  ScholarshipRepository                      │     │
│  │  EligibilityCriteriaRepository              │     │
│  │  LinkRepository                             │     │
│  │  CrawlJobRepository                         │     │
│  │  LLMCallLogRepository                       │     │
│  └─────────────────────────────────────────────┘     │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
      ┌─────────────────┐
      │   MySQL 8.0     │
      │   (aiomysql)    │
      └─────────────────┘
```

---

## Features

- **Dual Crawling Strategy**: Scrapy batch crawls + BeautifulSoup on-demand
- **LLM-Assisted Extraction**: OpenAI (gpt-4o-mini) primary, Anthropic (claude-sonnet-4) fallback
- **4-Dimension Linking**: University (50%), Field (30%), Degree (15%), Geographic (5%) confidence scoring
- **Program-scoped search**: Optional `program_ids` on `POST /api/v1/scholarships/search` limits results to scholarships linked in `scholarship_program_links`
- **Centralized region data**: `app/utils/region_mapping.py` backs eligibility `region` criteria and the geographic linking dimension
- **Eligibility Filtering**: Strict binary matching against student profiles (mandatory vs preferred criteria)
- **Scheduled Crawls**: APScheduler for weekly batch updates (Sunday 3 AM UTC)
- **Service Auth**: X-Service-Token middleware (orchestrator-only access)
- **Raw SQL**: aiomysql with repository pattern (no ORM)
- **LLM Cost Tracking**: Token usage and cost per API call logged to database
- **Scholarship Staleness**: Auto-flag scholarships not crawled in 30+ days
- **Graceful Degradation**: Falls back to regex extraction when LLM is unavailable
- **Docker-First**: Compose for local dev, Kubernetes-ready

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Runtime |
| MySQL | 8.0+ | Database |
| Docker | 24.0+ | Containerised deployment (optional) |

---

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/maugus0/ouroboros-ai-scholarship-discovery.git
cd ouroboros-ai-scholarship-discovery

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
DB_HOST=localhost
DB_NAME=ouroboros_scholarship_db
DB_USERNAME=root
DB_PASSWORD=your_mysql_password

X_SERVICE_TOKEN=your-48-char-random-token
OPENAI_API_KEY=sk-your-openai-key
```

### 3. Generate Service Token

```bash
python scripts/generate_service_token.py
# Add output to .env as X_SERVICE_TOKEN
```

### 4. Database Setup

**Option A: Docker (Recommended)**

```bash
docker compose up mysql -d
docker compose logs -f mysql   # wait for "ready for connections"
```

**Option B: Local MySQL**

```bash
mysql -u root -p -e "CREATE DATABASE ouroboros_scholarship_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 5. Run Migrations

```bash
python scripts/run_migrations.py
```

Expected output:

```
Running migration: 001_create_scholarships.sql
  ✓ 001_create_scholarships.sql applied
Running migration: 002_create_eligibility_criteria.sql
  ✓ 002_create_eligibility_criteria.sql applied
Running migration: 003_create_scholarship_program_links.sql
  ✓ 003_create_scholarship_program_links.sql applied
Running migration: 004_create_crawl_jobs.sql
  ✓ 004_create_crawl_jobs.sql applied
Running migration: 005_create_llm_call_logs.sql
  ✓ 005_create_llm_call_logs.sql applied

All migrations applied successfully.
```

### 6. Seed Scholarship Sources

```bash
python scripts/seed_scholarship_sources.py
```

### 7. Start the Service

```bash
chmod +x start.sh
./start.sh
# or: uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### 8. Verify Health

```bash
curl http://localhost:8003/health
# {"status":"healthy","version":"0.1.0","database":"not_connected"}
```

Swagger docs are available at `http://localhost:8003/docs`.

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| **Database** ||||
| `DB_HOST` | No | `localhost` | MySQL host |
| `DB_PORT` | No | `3306` | MySQL port |
| `DB_NAME` | No | `ouroboros_scholarship_db` | Database name |
| `DB_USERNAME` | No | `root` | MySQL user |
| `DB_PASSWORD` | Yes | — | MySQL password |
| `DB_POOL_SIZE` | No | `10` | Max connections in pool |
| **Inter-Service Auth** ||||
| `X_SERVICE_TOKEN` | Yes | — | Shared secret for orchestrator calls |
| **LLM Configuration** ||||
| `OPENAI_API_KEY` | No | — | OpenAI API key (primary) |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model |
| `OPENAI_TEMPERATURE` | No | `0.1` | Low for structured extraction |
| `ANTHROPIC_API_KEY` | No | — | Anthropic API key (fallback) |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-20250514` | Anthropic model |
| **Crawling** ||||
| `SCRAPY_CONCURRENT_REQUESTS` | No | `8` | Max concurrent crawl requests |
| `SCRAPY_DOWNLOAD_DELAY` | No | `2.0` | Seconds between requests |
| `RESPECT_ROBOTS_TXT` | No | `true` | Obey robots.txt |
| `SCHOLARSHIP_STALENESS_DAYS` | No | `30` | Re-crawl after N days |
| `BATCH_CRAWL_CRON` | No | `0 3 * * 0` | Weekly batch schedule |
| **4-Dimension Linking** ||||
| `LINKING_WEIGHT_UNIVERSITY` | No | `50` | University match weight |
| `LINKING_WEIGHT_FIELD` | No | `30` | Field match weight |
| `LINKING_WEIGHT_DEGREE` | No | `15` | Degree match weight |
| `LINKING_WEIGHT_GEOGRAPHIC` | No | `5` | Geographic match weight |
| `MIN_LINK_CONFIDENCE_SCORE` | No | `0.40` | Only store links >= 40% |
| **Application** ||||
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `USE_MOCK_DATA` | No | `true` | Use mocks in tests |
| `ALLOW_DB_FAILURE` | No | `false` | Continue if DB unavailable |
| **Docker** ||||
| `DOCKER_MYSQL_PORT` | No | `3310` | Host port for MySQL |

### Docker / CI Prefix Compatibility

| `DB_*` Prefix | Equivalent `MYSQL_*` |
|---------------|---------------------|
| `DB_HOST` | `MYSQL_HOST` |
| `DB_NAME` | `MYSQL_DATABASE` |
| `DB_USERNAME` | `MYSQL_USER` |
| `DB_PASSWORD` | `MYSQL_PASSWORD` |
| `DB_PORT` | `MYSQL_PORT` |

---

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `scholarships` | Scholarship metadata with eligibility JSON |
| `eligibility_criteria` | Granular criteria entries (mandatory vs preferred) |
| `scholarship_program_links` | Many-to-many links with 4-dimension confidence scores |
| `crawl_jobs` | Async crawl job tracking |
| `llm_call_logs` | LLM usage audit trail with cost tracking |

### Relationships

```
scholarships    (1) ──< (N) eligibility_criteria
scholarships    (N) ──< (N) programs (via scholarship_program_links)
```

### Migrations

Run in order via `python scripts/run_migrations.py`:

```
migrations/
├── 001_create_scholarships.sql
├── 002_create_eligibility_criteria.sql
├── 003_create_scholarship_program_links.sql
├── 004_create_crawl_jobs.sql
└── 005_create_llm_call_logs.sql
```

---

## API Endpoints

**Base URL**: `http://localhost:8003`

All endpoints except health checks require the `X-Service-Token` header.

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Root health check |
| GET | `/health` | No | Detailed health status |

### Scholarship Search

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/scholarships/search` | X-Service-Token | Search and filter scholarships |
| GET | `/api/v1/scholarships/{id}` | X-Service-Token | Get full scholarship details + criteria |

**POST `/api/v1/scholarships/search` — request body:**

```json
{
  "student_profile": {
    "gpa": 3.8,
    "gpa_scale": 4.0,
    "nationality": "India",
    "field_of_study": "Computer Science",
    "degree_type": "master",
    "language_test": "IELTS 7.5"
  },
  "program_ids": ["prog-123", "prog-456"],
  "provider": "DAAD",
  "max_results": 20,
  "page": 1
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `student_profile` | No | When provided, filters scholarships by eligibility |
| `student_profile.gpa_scale` | No | GPA scale (default 4.0) for normalization |
| `program_ids` | No | Filter to scholarships linked to these programs |
| `provider` | No | Substring match on provider name |
| `max_results` | No | Page size (1-100, default 20) |
| `page` | No | Page number (default 1) |

### Scholarship-Program Linking

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/scholarships/by-program/{program_id}` | X-Service-Token | Get linked scholarships sorted by confidence |
| POST | `/api/v1/scholarships/link` | X-Service-Token | Create/update a scholarship-program link |

### Crawl Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/scholarships/crawl` | X-Service-Token | Trigger on-demand or batch crawl |
| GET | `/api/v1/scholarships/crawl/{job_id}` | X-Service-Token | Get crawl job status |
| GET | `/api/v1/scholarships/crawl` | X-Service-Token | List crawl jobs |

### Error Responses

| Status | Meaning |
|--------|---------|
| 401 | Missing `X-Service-Token` header |
| 403 | Invalid `X-Service-Token` |
| 404 | Resource not found |
| 422 | Validation error |
| 502 | Upstream error (LLM, crawl failure) |
| 503 | Service unavailable (database down) |

Interactive docs: `http://localhost:8003/docs`.

---

## Prompt System

Prompts are **JSON templates** in `prompts/` and are loaded at runtime with optional context injection.

### Available prompts

| File | Purpose |
|------|---------|
| `scholarship_extraction_v1.json` | Extract structured scholarship fields from page text |
| `eligibility_parsing_v1.json` | Parse natural-language eligibility into structured criteria |
| `field_classification_v1.json` | Classify scholarship field and broad category |

---

## 4-Dimension Linking Algorithm

This is the **key differentiator** from Program Discovery Agent. When the Orchestrator passes `program_id` and program metadata, this service calculates a confidence score across 4 dimensions:

### Dimensions and Weights (configurable via env vars, must sum to 100)

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **University Match** | 50% | Direct match: scholarship provider == program university |
| **Field Match** | 30% | Subject classification overlap (keyword-based + Jaccard similarity) |
| **Degree Match** | 15% | Bachelor / Master / PhD alignment |
| **Geographic Match** | 5% | Region/nationality restrictions vs program country (macro-regions via `app/utils/region_mapping.py`) |

### Formula

```
confidence = Σ (dimension_score × dimension_weight / 100)
```

### Example

```
MIT Presidential Fellowship → MIT Computer Science MS
- University match: 1.0 (same university)
- Field match: 0.9 (CS in STEM)
- Degree match: 1.0 (both master's)
- Geographic match: 1.0 (no restriction)
→ Confidence: 0.50×1.0 + 0.30×0.9 + 0.15×1.0 + 0.05×1.0 = 0.97 (97%)
```

Only links with confidence >= `MIN_LINK_CONFIDENCE_SCORE` (default 0.40) are stored.

---

## Eligibility Filtering

Strict binary matching: student must meet **ALL mandatory** criteria to be eligible.

### Supported Criterion Types

| Type | Comparison | Example |
|------|-----------|---------|
| `min_gpa` | Student GPA >= required | 3.8 >= 3.5 |
| `nationality` | Exact match in allowed list | "India" in "India,China,Japan" |
| `region` | Country-to-region mapping | "India" in Asia region |
| `field_of_study` | Exact match in allowed list | "Computer Science" in "CS,Engineering" |
| `degree_level` | Exact match in allowed list | "master" in "master,phd" |
| `language_test` | Test name match + score >= required | IELTS 7.5 >= IELTS 7.0 |

Non-mandatory criteria (preferred/recommended) are **not** blocking.

Macro-region labels for `region` criteria use the same country lists as geographic linking (`app/utils/region_mapping.py`); extend that module to add countries or regions consistently.

---

## Crawling Strategy

### Batch mode (Scrapy)

- **Schedule**: Weekly (Sunday 3 AM UTC) via APScheduler
- **Targets**: Scholarship databases (CSC, Chevening, Fulbright, DAAD), university financial aid pages
- **Concurrency**: Up to 8 simultaneous requests; 4 per domain

### On-demand mode (httpx + BeautifulSoup)

- **Trigger**: Orchestrator POST to `/api/v1/scholarships/crawl`
- **Use case**: On-demand scrape for a `target_url`, or a listing/source page via `target_source` (discovers child links, then crawls each)

### Ethics and rate limiting

| Setting | Default | Description |
|---------|---------|-------------|
| `ROBOTSTXT_OBEY` | `True` | Respect robots.txt |
| `SCRAPY_DOWNLOAD_DELAY` | `2.0` | Minimum seconds between requests |
| `MIN_CRAWL_DELAY_SECONDS` / `MAX_CRAWL_DELAY_SECONDS` | `2` / `5` | On-demand jittered delay |
| `SCRAPY_CONCURRENT_REQUESTS` | `8` | Global concurrency cap |

---

## Development Workflow

### Code Quality Checks

```bash
black app/ tests/
isort app/ tests/
flake8 app/ tests/ --max-line-length=120 --extend-ignore=E203,W503,E501
pylint app/ tests/
mypy app/ --ignore-missing-imports --no-strict-optional
ALLOW_DB_FAILURE=true pytest tests/ -v
```

### Pre-Commit Script

```bash
chmod +x pre-commit-check.sh
./pre-commit-check.sh
```

---

## Testing

### Run All Tests

```bash
ALLOW_DB_FAILURE=true USE_MOCK_DATA=true X_SERVICE_TOKEN=test-service-token pytest tests/ -v
```

### Run with Coverage

```bash
ALLOW_DB_FAILURE=true pytest tests/ --cov=app --cov-report=html -v
open htmlcov/index.html
```

### Test Structure

```
tests/
├── conftest.py                              # Shared fixtures
├── fake_repos.py                            # In-memory repository mocks
├── unit/
│   ├── test_config.py                       # Configuration loading
│   ├── test_health.py                       # Health check endpoints
│   ├── test_main.py                         # FastAPI application
│   ├── test_security.py                     # X-Service-Token validation
│   ├── test_exceptions.py                   # Custom exception classes
│   ├── test_models.py                       # Pydantic model validation
│   ├── test_linking_service.py              # 4-dimension scoring logic
│   ├── test_eligibility_filter.py           # Student matching logic
│   ├── test_llm_service.py                  # LLM fallback (mocked)
│   ├── test_llm_prompts.py                  # Prompt template loading
│   ├── test_prompt_utils.py                 # Prompt building utilities
│   ├── test_html_parser.py                  # BeautifulSoup extraction
│   ├── test_html_utils.py                   # URL/HTML utility functions
│   └── test_scrapy_pipeline.py              # Scrapy data validation
└── integration/
    ├── test_scholarship_search_flow.py      # HTTP search + filtering
    └── test_crawl_job_flow.py               # HTTP crawl trigger + status
```

---

## CI/CD Pipeline

**Workflow**: `.github/workflows/deploy.yml`

**Triggers**:
- Pull requests to `main` or `develop` (opened, synchronize, reopened)
- Push to `main` (triggers Docker push to GHCR + Trivy scan)

**Concurrency**: Superseded runs on the same ref are auto-cancelled to save runner minutes.

### Pipeline Stages

| Stage | Job Name | Description |
|-------|----------|-------------|
| **1** | `format` | Black + isort validation |
| **1** | `lint` | flake8 + pylint |
| **1** | `unit-tests` | pytest with JUnit XML output |
| **2** | `type-check` | mypy static analysis (needs Stage 1) |
| **2** | `integration-tests` | pytest with coverage HTML + XML (needs Stage 1) |
| **2** | `security-static` | Bandit static analysis with `bandit.yaml` config |
| **2** | `security-scan` | Snyk OSS dependency scan (skipped if no `SNYK_TOKEN`) |
| **3** | `docker-build` | Build & push to GHCR (push to main only) |
| **4** | `trivy-scan` | Container vulnerability scan (push to main only) |
| **5** | `reports-summary` | Consolidated CI report bundle |

### Pipeline Graph

```
                    ┌──> type-check ────────────┐
format  ───┐        │                           │
           ├────────┼──> integration-tests ─────┤
lint    ───┤        │                           ├──> docker-build ──> trivy-scan ──> reports-summary
           │        ├──> security-static ───────┤         │
unit-tests ┴────────┼──> security-scan ─────────┘         │
                    │                                     │
                    └─────────────────────────────────────┘
```

### Security Scans

| Tool | Scope | Config |
|------|-------|--------|
| **Bandit** | Static Python code analysis | `bandit.yaml` (inline `# nosec B###` for false positives) |
| **Snyk OSS** | Dependency vulnerabilities | Requires `SNYK_TOKEN` secret; `continue-on-error: true` |
| **Trivy** | Container image vulnerabilities | Runs on GHCR image after push to main |

### Artifacts

| Artifact | Contents |
|----------|----------|
| `test-results` | JUnit XML from unit tests |
| `coverage-report` | HTML coverage report |
| `coverage-xml` | Cobertura XML for dashboards |
| `security-reports-bandit` | Bandit JSON report |
| `snyk-sarif` | Snyk SARIF for Code Scanning |
| `trivy-report` | Trivy JSON vulnerability report |
| `ci-reports` | Consolidated summary markdown |

---

## Deployment

### Docker Compose (full stack)

```bash
docker compose up --build -d
docker compose logs -f
docker compose down
docker compose down -v
```

### MySQL only (app on host)

```bash
docker compose up mysql -d
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### Port assignments (platform)

| Service | HTTP port | MySQL host port |
|---------|-----------|----------------|
| Orchestrator | 8000 | 3307 |
| Student Profile | 8001 | 3308 |
| Program Discovery | 8002 | 3309 |
| **Scholarship Discovery** | **8003** | **3310** |
| Eligibility Engine | 8004 | — (PostgreSQL) |
| Application Support | 8005 | 3311 |

---

## Project Structure

```
ouroboros-ai-scholarship-discovery/
├── app/
│   ├── api/                            # Route handlers (thin layer)
│   │   ├── health.py                   # GET / and /health
│   │   ├── scholarships.py            # POST /search, GET /{id}
│   │   ├── linking.py                 # GET /by-program/{pid}, POST /link
│   │   └── crawl.py                   # POST /crawl, GET /crawl/{id}
│   ├── core/                           # Infrastructure
│   │   ├── logging.py                 # structlog configuration
│   │   └── security.py               # X-Service-Token validation
│   ├── crawlers/                       # Web crawling layer
│   │   ├── scrapy/                    # Batch crawling
│   │   │   ├── spiders/              # Scrapy spider classes
│   │   │   ├── middlewares.py        # User-agent rotation + Scrapy 2.11+ compatible retry
│   │   │   ├── pipelines.py         # Data validation + storage
│   │   │   └── settings.py          # Scrapy config
│   │   ├── parsers/                   # Page parsing
│   │   │   ├── html_parser.py       # BeautifulSoup helpers
│   │   │   └── llm_parser.py        # LLM-assisted extraction
│   │   └── on_demand_crawler.py      # httpx-based targeted scraping
│   ├── llm/                            # LLM integration
│   │   ├── openai_client.py          # Primary provider + retry
│   │   ├── anthropic_client.py       # Fallback provider + retry
│   │   ├── prompts.py                # Prompt builder functions
│   │   └── schemas.py                # Output validation schemas
│   ├── models/                         # Pydantic request/response schemas
│   │   ├── common_models.py          # StandardResponse, pagination
│   │   ├── scholarship.py            # Search request/response
│   │   ├── eligibility.py            # Criterion models
│   │   ├── linking.py                # Program linking models
│   │   └── crawl.py                  # Crawl job models
│   ├── repositories/                   # Raw SQL data access (aiomysql)
│   │   ├── db_pool.py                # Connection pool management
│   │   ├── mysql_base.py            # Base repository
│   │   ├── mysql_scholarship_repo.py # Scholarships CRUD + search
│   │   ├── mysql_eligibility_criteria_repo.py # Criteria CRUD
│   │   ├── mysql_link_repo.py        # Scholarship-program links
│   │   ├── mysql_crawl_job_repo.py   # Crawl job tracking
│   │   └── mysql_llm_call_log_repo.py # LLM audit logging
│   ├── services/                       # Business logic
│   │   ├── scholarship_service.py    # Search + store
│   │   ├── eligibility_filter_service.py # Student profile matching
│   │   ├── linking_service.py        # 4-dimension scoring
│   │   ├── crawl_service.py          # Crawl job management
│   │   ├── llm_service.py           # LLM provider fallback
│   │   └── scheduler_service.py     # APScheduler batch crawls
│   ├── middleware/                      # HTTP middleware
│   │   ├── service_auth.py          # X-Service-Token dependency
│   │   └── logging_middleware.py    # Trace ID + latency logging
│   ├── utils/                          # Utilities
│   │   ├── exceptions.py            # Custom exception hierarchy
│   │   ├── trace_id.py              # UUID-v4 trace ID
│   │   ├── helpers.py               # generate_uuid, timestamps
│   │   ├── timezone.py              # UTC helpers
│   │   ├── prompt_utils.py          # JSON template loading
│   │   ├── html_utils.py            # URL validation, text cleaning
│   │   └── region_mapping.py       # Region ↔ country lists (eligibility + linking)
│   ├── config.py                       # Pydantic settings
│   └── main.py                         # FastAPI app with lifespan
├── migrations/                         # SQL migration files (001-005)
├── prompts/                            # JSON prompt templates
│   ├── scholarship_extraction_v1.json
│   ├── eligibility_parsing_v1.json
│   └── field_classification_v1.json
├── scripts/
│   ├── run_migrations.py              # Execute migrations
│   ├── seed_scholarship_sources.py    # Load top scholarship sources
│   ├── generate_service_token.py      # Generate X_SERVICE_TOKEN
│   └── trigger_batch_crawl.py         # Manual batch crawl
├── tests/
│   ├── unit/                           # Unit tests (14 files)
│   └── integration/                    # Integration tests (2 files)
├── .github/workflows/
│   └── deploy.yml                      # 7-job CI/CD pipeline
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── pytest.ini
├── .flake8
├── .pylintrc
├── bandit.yaml                          # Bandit security scan config
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── start.sh
├── pre-commit-check.sh
└── README.md
```

---

## Troubleshooting

### Database Connection Failed

**Symptom**: `RuntimeError: Database pool has not been initialised`

```bash
docker compose ps
mysql -h localhost -P 3310 -u root -p -e "SHOW DATABASES;"
grep DB_ .env
```

### LLM Extraction Fails

**Symptom**: `LLMExtractionError: Both LLM providers failed`

```bash
grep API_KEY .env
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'app'`

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Attribution

**Developed by**: OuroborosAI Developer Team

**Project**: Ouroboros AI Scholarship Discovery Platform

**Repository**: [github.com/maugus0/ouroboros-ai-scholarship-discovery](https://github.com/maugus0/ouroboros-ai-scholarship-discovery)
