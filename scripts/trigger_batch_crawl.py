"""Manually trigger a batch crawl (useful for testing and initial data load)."""

import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")


async def main():
    from app.services.crawl_service import CrawlService

    service = CrawlService()
    job_id = await service.create_job({"job_type": "batch"})
    print(f"Batch crawl job created: {job_id}")
    print("Note: The crawl runs as a background task in the API server.")
    print("Use GET /api/v1/scholarships/crawl/{job_id} to check status.")


if __name__ == "__main__":
    asyncio.run(main())
