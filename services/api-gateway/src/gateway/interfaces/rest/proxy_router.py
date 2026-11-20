from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from gateway.domain.model.authenticated_user import AuthenticatedUser
from gateway.interfaces.rest.security.auth_dependencies import (
    require_posting_api_key,
    require_user,
)

router = APIRouter(tags=["Proxy"])


def _trace_header(request: Request) -> dict[str, str]:
    trace_id = request.headers.get("X-Trace-Id")
    return {"X-Trace-Id": trace_id} if trace_id else {}


async def _read_json_body(request: Request) -> Any | None:
    raw = await request.body()
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return JSONResponse(  # type: ignore[return-value]
            status_code=400,
            content={
                "type": "about:blank",
                "title": "Invalid JSON body",
                "status": 400,
                "detail": "Request body is not valid JSON.",
                "trace_id": request.headers.get("X-Trace-Id", "unknown"),
            },
        )


# ---------- transactions ----------

@router.post("/api/v1/transactions")
async def post_transaction(
    request: Request,
    _: None = Depends(require_posting_api_key),
) -> Response:
    client = request.app.state.proxy_client
    body = await _read_json_body(request)
    if isinstance(body, JSONResponse):
        return body
    return await client.forward(
        method="POST",
        base_url=request.app.state.transaction_service_url,
        path="/api/v1/transactions",
        headers={**_trace_header(request),
                 **{k: v for k, v in request.headers.items()
                    if k.lower() == "idempotency-key"}},
        body=body,
    )


@router.get("/api/v1/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: UUID,
    request: Request,
    user: AuthenticatedUser = Depends(require_user),
) -> Response:
    client = request.app.state.proxy_client
    return await client.forward(
        method="GET",
        base_url=request.app.state.transaction_service_url,
        path=f"/api/v1/transactions/{transaction_id}",
        headers=_trace_header(request),
    )


# ---------- scores ----------

@router.post("/api/v1/scores")
async def post_score(
    request: Request,
    user: AuthenticatedUser = Depends(require_user),
) -> Response:
    client = request.app.state.proxy_client
    body = await _read_json_body(request)
    if isinstance(body, JSONResponse):
        return body
    return await client.forward(
        method="POST",
        base_url=request.app.state.scoring_service_url,
        path="/api/v1/scores",
        headers={**_trace_header(request),
                 **{k: v for k, v in request.headers.items()
                    if k.lower() == "idempotency-key"}},
        body=body,
    )


@router.get("/api/v1/scores/{scoring_result_id}")
async def get_score(
    scoring_result_id: UUID,
    request: Request,
    user: AuthenticatedUser = Depends(require_user),
) -> Response:
    client = request.app.state.proxy_client
    return await client.forward(
        method="GET",
        base_url=request.app.state.scoring_service_url,
        path=f"/api/v1/scores/{scoring_result_id}",
        headers=_trace_header(request),
    )


# ---------- alerts ----------

@router.get("/api/v1/alerts")
async def list_alerts(
    request: Request,
    user: AuthenticatedUser = Depends(require_user),
) -> Response:
    client = request.app.state.proxy_client
    return await client.forward(
        method="GET",
        base_url=request.app.state.alert_service_url,
        path="/api/v1/alerts",
        headers=_trace_header(request),
        query=dict(request.query_params),
    )


@router.get("/api/v1/alerts/{alert_id}")
async def get_alert(
    alert_id: UUID,
    request: Request,
    user: AuthenticatedUser = Depends(require_user),
) -> Response:
    client = request.app.state.proxy_client
    return await client.forward(
        method="GET",
        base_url=request.app.state.alert_service_url,
        path=f"/api/v1/alerts/{alert_id}",
        headers=_trace_header(request),
    )


@router.patch("/api/v1/alerts/{alert_id}/assign")
async def assign_alert(
    alert_id: UUID,
    request: Request,
    user: AuthenticatedUser = Depends(require_user),
) -> Response:
    # The analyst_id is pulled from the JWT; whatever the client sends is overridden.
    client = request.app.state.proxy_client
    body = await _read_json_body(request) or {}
    if isinstance(body, JSONResponse):
        return body
    body["analyst_id"] = str(user.analyst_id)
    return await client.forward(
        method="PATCH",
        base_url=request.app.state.alert_service_url,
        path=f"/api/v1/alerts/{alert_id}/assign",
        headers=_trace_header(request),
        body=body,
    )


@router.patch("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: UUID,
    request: Request,
    user: AuthenticatedUser = Depends(require_user),
) -> Response:
    client = request.app.state.proxy_client
    body = await _read_json_body(request)
    if isinstance(body, JSONResponse):
        return body
    return await client.forward(
        method="PATCH",
        base_url=request.app.state.alert_service_url,
        path=f"/api/v1/alerts/{alert_id}/resolve",
        headers=_trace_header(request),
        body=body,
    )


@router.patch("/api/v1/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: UUID,
    request: Request,
    user: AuthenticatedUser = Depends(require_user),
) -> Response:
    client = request.app.state.proxy_client
    body = await _read_json_body(request)
    if isinstance(body, JSONResponse):
        return body
    return await client.forward(
        method="PATCH",
        base_url=request.app.state.alert_service_url,
        path=f"/api/v1/alerts/{alert_id}/dismiss",
        headers=_trace_header(request),
        body=body,
    )


# ---------- analytics ----------

@router.get("/analytics/{sub_path:path}")
async def proxy_analytics(
    sub_path: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_user),
) -> Response:
    # The JWT is replaced by the analytics API key: internal services
    # trust the gateway, not the analyst's token.
    client = request.app.state.proxy_client
    return await client.forward(
        method="GET",
        base_url=request.app.state.analytics_service_url,
        path=f"/analytics/{sub_path}",
        headers={
            **_trace_header(request),
            "X-API-Key": request.app.state.analytics_api_key,
        },
        query=dict(request.query_params),
    )
