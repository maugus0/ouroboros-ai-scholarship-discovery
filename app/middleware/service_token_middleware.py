"""ASGI middleware for inter-service X-Service-Token validation."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import validate_service_token


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
        """Protect versioned API routes with X-Service-Token."""
        path = request.url.path
        if path in self.PUBLIC_PATHS or not path.startswith("/api/v1/"):
            return await call_next(request)

        try:
            validate_service_token(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        return await call_next(request)
