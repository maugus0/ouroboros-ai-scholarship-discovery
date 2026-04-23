"""ASGI middleware for inter-service Bearer token validation."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.service_auth import require_service_token


class ServiceTokenMiddleware(BaseHTTPMiddleware):
    """Validate service tokens before protected API handlers run."""

    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Protect versioned API routes with Bearer token."""
        path = request.url.path
        if path in self.PUBLIC_PATHS or not path.startswith("/api/v1/"):
            return await call_next(request)

        try:
            await require_service_token(request)
        except Exception as exc:
            status_code = getattr(exc, "status_code", 401)
            detail = getattr(exc, "detail", "Token validation failed")
            return JSONResponse(status_code=status_code, content={"detail": detail})

        return await call_next(request)
