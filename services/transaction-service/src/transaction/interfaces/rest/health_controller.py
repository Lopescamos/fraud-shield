from __future__ import annotations

from fastapi import APIRouter, Request, Response
from sqlalchemy import text

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "UP"}


@router.get("/ready")
async def ready(request: Request) -> Response:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        return Response(status_code=503)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return Response(status_code=503)
    return Response(status_code=200)
