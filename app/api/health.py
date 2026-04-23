"""Health-check endpoints."""

from fastapi import APIRouter

from app.config import APP_VERSION
from app.repositories.db_pool import is_database_connected

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    return {
        "message": "Scholarship Discovery Agent",
        "version": APP_VERSION,
        "status": "healthy",
    }


@router.get("/health")
async def health_check():
    database_status = "connected" if await is_database_connected() else "not_connected"
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "database": database_status,
    }
