from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

HEADER_NAME = "X-API-Key"
# Endpoints that must stay reachable without a key.
_PUBLIC_PREFIXES: tuple[str, ...] = ("/health", "/ready", "/docs", "/openapi.json", "/redoc")


def register(app: FastAPI, allowed_keys: set[str]) -> None:
    """Register an ASGI middleware that checks X-API-Key on every call
    except the health/docs endpoints. 401 is returned as Problem Details
    so Power BI surfaces a clear error."""

    @app.middleware("http")
    async def _api_key_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable],
    ):
        path = request.url.path
        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        sent = request.headers.get(HEADER_NAME)
        if sent is None or sent not in allowed_keys:
            return JSONResponse(
                status_code=401,
                content={
                    "type": "about:blank",
                    "title": "Missing or invalid API key",
                    "status": 401,
                    "detail": f"Header '{HEADER_NAME}' is required.",
                    "trace_id": request.headers.get("X-Trace-Id", "unknown"),
                },
            )
        return await call_next(request)
