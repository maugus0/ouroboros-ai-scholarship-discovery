"""Report database quality after importing scholarship spider output."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

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


MOJIBAKE_MARKERS = ("鈥", "檌", "枚", "茅", "麓", "么", "榓", "淲", "�")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Check imported scholarship database quality.")
    parser.add_argument("--provider", default=None, help="Only include scholarships from this provider.")
    parser.add_argument("--active-only", action="store_true", help="Only include active scholarships.")
    parser.add_argument("--sample-limit", type=int, default=10, help="Number of anomaly samples to show.")
    return parser.parse_args()


def where_clause(provider: str | None, active_only: bool, table_alias: str | None = None) -> tuple[str, list[Any]]:
    """Build a reusable WHERE clause."""
    conditions = []
    params: list[Any] = []
    prefix = f"{table_alias}." if table_alias else ""
    if provider:
        conditions.append(f"{prefix}provider = %s")
        params.append(provider)
    if active_only:
        conditions.append(f"{prefix}is_active = TRUE")
    return ("WHERE " + " AND ".join(conditions), params) if conditions else ("", params)


def pct(value: int, total: int) -> str:
    """Format a percentage safely."""
    return "0.0%" if total == 0 else f"{value / total * 100:.1f}%"


def has_json_value(value: Any) -> bool:
    """Return True when a DB JSON/text field contains useful data."""
    if value in (None, "", {}, []):
        return False
    if isinstance(value, (dict, list)):
        return bool(value)
    if not isinstance(value, str):
        return True
    text = value.strip()
    if text in ("{}", "[]", "null"):
        return False
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return bool(text)
    return bool(parsed)


def contains_mojibake(row: dict[str, Any]) -> bool:
    """Detect common UTF-8-as-GBK mojibake fragments."""
    text = " ".join(str(row.get(key) or "") for key in ("name", "description", "eligibility_criteria", "application_requirements"))
    return any(marker in text for marker in MOJIBAKE_MARKERS)


async def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Run a SELECT query and return rows as dictionaries."""
    import aiomysql

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchall()


async def main() -> None:
    """Check import coverage and common anomalies."""
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
        where_sql, params = where_clause(args.provider, args.active_only)
        rows = await fetch_all(
            f"""
            SELECT id, name, provider, source_url, funding_amount, currency, deadline,
                   description, eligibility_criteria, application_requirements,
                   crawled_at, created_at, updated_at, is_active
            FROM scholarships
            {where_sql}
            ORDER BY updated_at DESC
            """,
            tuple(params),
        )

        total = len(rows)
        duplicate_rows = await fetch_all(
            f"""
            SELECT source_url, COUNT(*) AS count
            FROM scholarships
            {where_sql}
            GROUP BY source_url
            HAVING COUNT(*) > 1
            ORDER BY count DESC, source_url
            LIMIT %s
            """,
            tuple(params + [args.sample_limit]),
        )
        criteria_where_sql, criteria_params = where_clause(args.provider, args.active_only, table_alias="s")
        criteria_summary = await fetch_all(
            f"""
            SELECT COUNT(ec.id) AS criteria_count,
                   COUNT(DISTINCT ec.scholarship_id) AS scholarships_with_criteria_rows
            FROM eligibility_criteria ec
            JOIN scholarships s ON s.id = ec.scholarship_id
            {criteria_where_sql}
            """,
            tuple(criteria_params),
        )

        with_name = sum(1 for row in rows if row.get("name"))
        with_source_url = sum(1 for row in rows if row.get("source_url"))
        with_description = sum(1 for row in rows if row.get("description"))
        with_funding_amount = sum(1 for row in rows if row.get("funding_amount") is not None)
        with_currency = sum(1 for row in rows if row.get("currency"))
        with_deadline = sum(1 for row in rows if row.get("deadline") is not None)
        with_eligibility = sum(1 for row in rows if has_json_value(row.get("eligibility_criteria")))
        with_application = sum(1 for row in rows if has_json_value(row.get("application_requirements")))
        mojibake_rows = [row for row in rows if contains_mojibake(row)]
        generic_name_rows = [
            row
            for row in rows
            if str(row.get("name") or "").strip().lower() in {"daad scholarship", "finding scholarships", "unknown scholarship"}
        ]

        print("Import Quality Report")
        print("=====================")
        print(f"provider filter: {args.provider or 'all'}")
        print(f"active only: {args.active_only}")
        print(f"total rows: {total}")
        print()
        print("Field coverage")
        print(f"- name: {with_name}/{total} ({pct(with_name, total)})")
        print(f"- source_url: {with_source_url}/{total} ({pct(with_source_url, total)})")
        print(f"- description: {with_description}/{total} ({pct(with_description, total)})")
        print(f"- funding_amount: {with_funding_amount}/{total} ({pct(with_funding_amount, total)})")
        print(f"- currency: {with_currency}/{total} ({pct(with_currency, total)})")
        print(f"- deadline: {with_deadline}/{total} ({pct(with_deadline, total)})")
        print(f"- eligibility_criteria: {with_eligibility}/{total} ({pct(with_eligibility, total)})")
        print(f"- application_requirements: {with_application}/{total} ({pct(with_application, total)})")
        if criteria_summary:
            criteria_count = int(criteria_summary[0]["criteria_count"] or 0)
            scholarships_with_criteria_rows = int(criteria_summary[0]["scholarships_with_criteria_rows"] or 0)
            print(
                f"- eligibility_criteria table coverage: "
                f"{scholarships_with_criteria_rows}/{total} ({pct(scholarships_with_criteria_rows, total)})"
            )
            print(f"- eligibility_criteria table rows: {criteria_count}")
        print()
        print("Anomalies")
        print(f"- duplicate source_url groups: {len(duplicate_rows)} shown")
        print(f"- generic names: {len(generic_name_rows)}")
        print(f"- suspected mojibake rows: {len(mojibake_rows)}")

        if duplicate_rows:
            print()
            print("Duplicate source_url samples")
            for row in duplicate_rows:
                print(f"- count={row['count']} source_url={row['source_url']}")

        if mojibake_rows:
            print()
            print("Suspected mojibake samples")
            for row in mojibake_rows[: args.sample_limit]:
                print(f"- {row['id']} | {row.get('name')} | {row.get('source_url')}")

        missing_important = [
            row
            for row in rows
            if not has_json_value(row.get("eligibility_criteria")) or not has_json_value(row.get("application_requirements"))
        ]
        if missing_important:
            print()
            print("Rows missing eligibility/application JSON")
            for row in missing_important[: args.sample_limit]:
                print(f"- {row['id']} | {row.get('name')} | {row.get('source_url')}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
