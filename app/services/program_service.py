"""Program metadata access with graceful fallback when the upstream repo is absent."""

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from app.repositories.mysql_program_repo import ProgramRepository
except ImportError:  # pragma: no cover - exercised indirectly in app startup
    ProgramRepository = None


class ProgramService:
    """Fetch active programs when the Program Discovery repository is available."""

    def __init__(self):
        self.program_repo = ProgramRepository() if ProgramRepository else None

    async def get_all_active(self) -> list[dict]:
        """Return active programs or an empty list when upstream storage is unavailable."""
        if self.program_repo is None:
            logger.warning("program_repository_unavailable")
            return []

        return await self.program_repo.get_all_active()
