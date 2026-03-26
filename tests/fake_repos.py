"""In-memory fake repositories for unit testing without a database."""

from typing import Any

from app.utils.helpers import generate_uuid


class FakeScholarshipRepository:
    """In-memory store that mimics ScholarshipRepository."""

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}

    async def create_scholarship(self, data: dict[str, Any]) -> str:
        scholarship_id = data.get("id") or generate_uuid()
        self._store[scholarship_id] = {"id": scholarship_id, **data}
        return scholarship_id

    async def get_by_id(self, scholarship_id: str) -> dict[str, Any] | None:
        return self._store.get(scholarship_id)

    async def search_scholarships(
        self,
        provider=None,
        field=None,
        scholarship_ids=None,
        limit=20,
        offset=0,
    ) -> list[dict[str, Any]]:
        items = list(self._store.values())
        if provider:
            items = [s for s in items if provider.lower() in (s.get("provider") or "").lower()]
        if field:
            needle = field.lower()
            items = [
                s
                for s in items
                if needle in (s.get("name") or "").lower() or needle in (s.get("description") or "").lower()
            ]
        if scholarship_ids is not None:
            if not scholarship_ids:
                return []
            allowed = set(scholarship_ids)
            items = [s for s in items if s["id"] in allowed]
        return items[offset : offset + limit]

    async def count_scholarships(self, provider=None, scholarship_ids=None) -> int:
        items = list(self._store.values())
        if provider:
            items = [s for s in items if provider.lower() in (s.get("provider") or "").lower()]
        if scholarship_ids is not None:
            if not scholarship_ids:
                return 0
            allowed = set(scholarship_ids)
            items = [s for s in items if s["id"] in allowed]
        return len(items)

    async def get_stale_scholarships(self, staleness_days=30) -> list[dict[str, Any]]:
        _ = staleness_days
        return []

    async def update_scholarship(self, scholarship_id: str, updates: dict[str, Any]) -> int:
        if scholarship_id not in self._store:
            return 0
        self._store[scholarship_id].update(updates)
        return 1

    async def deactivate_scholarship(self, scholarship_id: str) -> int:
        if scholarship_id in self._store:
            self._store[scholarship_id]["is_active"] = False
            return 1
        return 0

    async def get_all_active(self, limit=1000) -> list[dict[str, Any]]:
        return [s for s in self._store.values() if s.get("is_active", True)][:limit]


class FakeEligibilityCriteriaRepository:
    """In-memory store that mimics EligibilityCriteriaRepository."""

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}

    async def create_criterion(self, data: dict[str, Any]) -> str:
        criterion_id = generate_uuid()
        self._store[criterion_id] = {"id": criterion_id, **data}
        return criterion_id

    async def bulk_create_criteria(self, criteria: list[dict[str, Any]]) -> int:
        count = 0
        for c in criteria:
            await self.create_criterion(c)
            count += 1
        return count

    async def get_by_scholarship_id(self, scholarship_id: str) -> list[dict[str, Any]]:
        return [c for c in self._store.values() if c.get("scholarship_id") == scholarship_id]

    async def get_mandatory_by_scholarship_id(self, scholarship_id: str) -> list[dict[str, Any]]:
        return [
            c for c in self._store.values() if c.get("scholarship_id") == scholarship_id and c.get("is_mandatory", True)
        ]

    async def delete_by_scholarship_id(self, scholarship_id: str) -> int:
        to_delete = [cid for cid, c in self._store.items() if c.get("scholarship_id") == scholarship_id]
        for cid in to_delete:
            del self._store[cid]
        return len(to_delete)


class FakeLinkRepository:
    """In-memory store that mimics LinkRepository."""

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}

    async def create_or_update(self, scholarship_id, program_id, link_type, confidence_score, match_metadata=None):
        link_id = generate_uuid()
        self._store[link_id] = {
            "id": link_id,
            "scholarship_id": scholarship_id,
            "program_id": program_id,
            "link_type": link_type,
            "confidence_score": confidence_score,
            "match_metadata": match_metadata,
        }
        return self._store[link_id]

    async def get_scholarship_ids_for_programs(self, program_ids, min_confidence=0.0) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for row in self._store.values():
            if row.get("program_id") not in program_ids:
                continue
            if row.get("confidence_score", 0) < min_confidence:
                continue
            sid = row.get("scholarship_id")
            if sid and sid not in seen:
                seen.add(sid)
                out.append(sid)
        return out

    async def get_by_program_id(self, program_id, min_confidence=0.0) -> list[dict[str, Any]]:
        return [
            row
            for row in self._store.values()
            if row.get("program_id") == program_id and row.get("confidence_score", 0) >= min_confidence
        ]

    async def get_by_scholarship_id(self, scholarship_id) -> list[dict[str, Any]]:
        return [row for row in self._store.values() if row.get("scholarship_id") == scholarship_id]

    async def delete_by_scholarship_id(self, scholarship_id) -> int:
        to_delete = [lid for lid, row in self._store.items() if row.get("scholarship_id") == scholarship_id]
        for lid in to_delete:
            del self._store[lid]
        return len(to_delete)

    async def count_links(self, min_confidence=0.0) -> int:
        return sum(1 for row in self._store.values() if row.get("confidence_score", 0) >= min_confidence)


class FakeCrawlJobRepository:
    """In-memory store that mimics CrawlJobRepository."""

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}

    async def create_job(self, data: dict[str, Any]) -> str:
        job_id = generate_uuid()
        self._store[job_id] = {"id": job_id, "status": "pending", **data}
        return job_id

    async def get_by_id(self, job_id: str) -> dict[str, Any] | None:
        return self._store.get(job_id)

    async def update_status(self, job_id, status, **kwargs) -> int:
        if job_id in self._store:
            self._store[job_id]["status"] = status
            self._store[job_id].update(kwargs)
            return 1
        return 0

    async def list_jobs(self, limit=20, offset=0, status=None) -> list[dict[str, Any]]:
        items = list(self._store.values())
        if status:
            items = [j for j in items if j.get("status") == status]
        return items[offset : offset + limit]

    async def get_running_jobs_count(self) -> int:
        return sum(1 for j in self._store.values() if j.get("status") == "running")
