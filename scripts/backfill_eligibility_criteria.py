"""Backfill eligibility_criteria rows from scholarships.eligibility_criteria JSON."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

import aiomysql
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from app.config import settings
from app.repositories.db_pool import DatabasePoolConfig, close_pool, create_pool, get_pool
from app.repositories.mysql_eligibility_criteria_repo import EligibilityCriteriaRepository
from app.services.eligibility_criteria_builder import EligibilityCriteriaBuilder


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Backfill eligibility_criteria table from scholarships JSON.")
    parser.add_argument("--provider", default=None, help="Only process scholarships from this provider.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N scholarships.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be written without changing DB.")
    return parser.parse_args()


async def fetch_scholarships(provider: str | None, limit: int | None) -> list[dict[str, Any]]:
    """Fetch scholarships with JSON eligibility payloads."""
    conditions = ["eligibility_criteria IS NOT NULL", "eligibility_criteria <> ''"]
    params: list[Any] = []
    if provider:
        conditions.append("provider = %s")
        params.append(provider)

    limit_sql = ""
    if limit is not None:
        limit_sql = "LIMIT %s"
        params.append(limit)

    query = f"""
        SELECT id, name, provider, source_url, eligibility_criteria, application_requirements
        FROM scholarships
        WHERE {" AND ".join(conditions)}
        ORDER BY updated_at DESC
        {limit_sql}
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query, tuple(params))
            return await cursor.fetchall()


async def count_criteria() -> int:
    """Count rows in eligibility_criteria."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT COUNT(*) AS count FROM eligibility_criteria")
            row = await cursor.fetchone()
            return int(row["count"])


async def main() -> None:
    """Backfill matching criteria for imported scholarships."""
    args = parse_args()
    await create_pool(
        DatabasePoolConfig(
            host=settings.get_db_host(),
            port=settings.get_db_port(),
            db=settings.get_db_name(),
            user=settings.get_db_user(),
            password=settings.get_db_password(),
            pool_size=settings.DB_POOL_SIZE,
        )
    )

    try:
        repo = EligibilityCriteriaRepository()
        rows = await fetch_scholarships(args.provider, args.limit)
        processed = 0
        inserted = 0
        empty = 0

        for row in rows:
            criteria = EligibilityCriteriaBuilder.build_from_scholarship(row)
            if not criteria:
                empty += 1
                continue

            processed += 1
            print(f"[{'dry-run' if args.dry_run else 'write'}] {row['name']} -> {len(criteria)} criteria")
            for criterion in criteria:
                print(
                    f"  - {criterion['criterion_type']}: {criterion['criterion_value']}"
                    f" mandatory={criterion.get('is_mandatory', True)}"
                )

            if args.dry_run:
                continue

            await repo.delete_by_scholarship_id(row["id"])
            for criterion in criteria:
                await repo.create_criterion(
                    {
                        "scholarship_id": row["id"],
                        "criterion_type": criterion["criterion_type"],
                        "criterion_value": criterion["criterion_value"],
                        "is_mandatory": criterion.get("is_mandatory", True),
                    }
                )
                inserted += 1

        total_criteria = await count_criteria()
        print()
        print("Backfill summary")
        print(f"- scholarships scanned: {len(rows)}")
        print(f"- scholarships with criteria: {processed}")
        print(f"- scholarships empty: {empty}")
        print(f"- criteria inserted this run: {inserted}")
        print(f"- criteria table total: {total_criteria}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
