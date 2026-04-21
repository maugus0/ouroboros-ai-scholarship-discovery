"""Import spider JSON output files through the app's crawl pipeline."""

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
from app.repositories.db_pool import DatabasePoolConfig, close_pool, create_pool
from app.services.crawl_service import CrawlService
from app.services.program_service import ProgramService


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Import spider JSON output files into the scholarship database."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Spider output JSON files. Defaults to chevening_output.json and daad_output.json if present.",
    )
    parser.add_argument(
        "--skip-linking",
        action="store_true",
        help="Skip scholarship-program linking during import.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only import the first N items from each file.",
    )
    return parser.parse_args()


def resolve_input_files(raw_files: list[str]) -> list[Path]:
    """Resolve user-provided or default spider output files."""
    if raw_files:
        files = [Path(file).expanduser() for file in raw_files]
    else:
        files = [
            ROOT_DIR / "chevening_output.json",
            ROOT_DIR / "daad_output.json",
        ]

    resolved: list[Path] = []
    for file in files:
        candidate = file if file.is_absolute() else ROOT_DIR / file
        if candidate.exists():
            resolved.append(candidate)
        else:
            print(f"[skip] file not found: {candidate}")

    if not resolved:
        raise FileNotFoundError("No input files found to import.")

    return resolved


def load_items(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    """Load a spider export file into a list of dict items."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]

    if not isinstance(payload, list):
        raise ValueError(f"{path} does not contain a JSON object or array.")

    items = [item for item in payload if isinstance(item, dict)]
    return items[:limit] if limit is not None else items


async def import_file(
    service: CrawlService,
    path: Path,
    active_programs: list[dict[str, Any]],
    limit: int | None = None,
) -> dict[str, Any]:
    """Import one spider output file through CrawlService."""
    items = load_items(path, limit=limit)
    job_id = await service.create_job(
        {
            "job_type": "on_demand",
            "target_source": str(path.name),
            "target_url": str(path),
        }
    )
    await service.crawl_job_repo.update_status(job_id, "running")

    imported = 0
    skipped = 0
    failed = 0

    try:
        for index, item in enumerate(items, start=1):
            if not item.get("source_url"):
                skipped += 1
                print(f"[skip] {path.name} item #{index} has no source_url")
                continue

            try:
                scholarship_id = await service._process_scraped_item(item, active_programs)
                imported += 1
                print(f"[ok] {path.name} item #{index} -> scholarship_id={scholarship_id}")
            except Exception as exc:  # pylint: disable=broad-exception-caught
                failed += 1
                print(f"[error] {path.name} item #{index}: {exc}")

        await service.crawl_job_repo.update_status(
            job_id,
            "completed",
            scholarships_crawled=imported,
            scholarships_updated=imported,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        await service.crawl_job_repo.update_status(job_id, "failed", error_message=str(exc))
        raise

    return {
        "job_id": job_id,
        "file": str(path),
        "total": len(items),
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
    }


async def main() -> None:
    """Import one or more spider output files into the database."""
    args = parse_args()
    files = resolve_input_files(args.files)

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
        service = CrawlService()
        active_programs: list[dict[str, Any]] = []
        if not args.skip_linking:
            active_programs = await ProgramService().get_all_active()
            print(f"Loaded {len(active_programs)} active programs for linking.")

        summaries = []
        for path in files:
            print(f"\nImporting {path} ...")
            summaries.append(
                await import_file(
                    service=service,
                    path=path,
                    active_programs=active_programs,
                    limit=args.limit,
                )
            )

        print("\nImport summary:")
        for summary in summaries:
            print(
                f"- {Path(summary['file']).name}: total={summary['total']}, "
                f"imported={summary['imported']}, skipped={summary['skipped']}, "
                f"failed={summary['failed']}, job_id={summary['job_id']}"
            )
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
