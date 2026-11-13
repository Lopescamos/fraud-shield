from __future__ import annotations

from typing import Any, NoReturn

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from alert.kernel.application.result import ApplicationError

_STATUS_FROM_CODE: dict[str, int] = {
    "validation_error": 422,
    "not_found": 404,
    "business_rule_violation": 409,
    "conflict": 409,
    "unexpected": 500,
}


def _trace_id_from(request: Request) -> str:
    return request.headers.get("X-Trace-Id", "unknown")


def raise_from_error(error: ApplicationError) -> NoReturn:
    status = _STATUS_FROM_CODE.get(error.code, 500)
    raise HTTPException(
        status_code=status,
        detail={
            "code": error.code,
            "title": error.title,
            "detail": error.detail,
        },
    )


def _problem(
    *,
    status: int,
    title: str,
    detail: str,
    trace_id: str,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "trace_id": trace_id,
    }
    if errors is not None:
        body["errors"] = errors
    return body


def register(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(p) for p in err.get("loc", ())),
                "message": err.get("msg", ""),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_problem(
                status=422,
                title="Validation failed",
                detail="One or more fields are invalid.",
                trace_id=_trace_id_from(request),
                errors=errors,
            ),
        )

    @app.exception_handler(HTTPException)
    async def _http_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        title = "Request failed"
        detail_text = ""
        if isinstance(detail, dict):
            title = str(detail.get("title", title))
            detail_text = str(detail.get("detail", ""))
        elif isinstance(detail, str):
            detail_text = detail
        return JSONResponse(
            status_code=exc.status_code,
            content=_problem(
                status=exc.status_code,
                title=title,
                detail=detail_text,
                trace_id=_trace_id_from(request),
            ),
        )
