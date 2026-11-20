from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from fastapi import Response

logger = logging.getLogger(__name__)

# Hop-by-hop headers that the gateway must not propagate.
_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)


class ProxyClient:
    """Thin wrapper around httpx.AsyncClient for proxying one request."""

    def __init__(self, timeout_seconds: int) -> None:
        self._timeout = timeout_seconds

    async def forward(
        self,
        *,
        method: str,
        base_url: str,
        path: str,
        headers: dict[str, str],
        query: dict[str, Any] | None = None,
        body: Any = None,
    ) -> Response:
        clean_headers = {
            k: v for k, v in headers.items() if k.lower() not in _HOP_BY_HOP
        }
        url = base_url.rstrip("/") + path
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                if body is None:
                    upstream = await client.request(
                        method, url, params=query, headers=clean_headers
                    )
                else:
                    upstream = await client.request(
                        method,
                        url,
                        params=query,
                        headers={**clean_headers, "content-type": "application/json"},
                        content=json.dumps(body).encode("utf-8"),
                    )
            except httpx.HTTPError as exc:
                logger.exception("upstream-call-failed", extra={"url": url})
                return Response(
                    content=json.dumps(
                        {
                            "type": "about:blank",
                            "title": "Upstream unavailable",
                            "status": 502,
                            "detail": str(exc),
                            "trace_id": clean_headers.get("x-trace-id", "unknown"),
                        }
                    ),
                    status_code=502,
                    media_type="application/problem+json",
                )
        response_headers = {
            k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP
        }
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
            media_type=upstream.headers.get("content-type", "application/json"),
        )
