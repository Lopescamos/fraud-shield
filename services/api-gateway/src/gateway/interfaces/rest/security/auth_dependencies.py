from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request

from gateway.application.auth_service import AuthService
from gateway.domain.model.authenticated_user import AuthenticatedUser
from gateway.kernel.application.result import Failure


def _auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def _problem(status: int, title: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"title": title, "detail": detail})


async def require_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    service: AuthService = Depends(_auth_service),
) -> AuthenticatedUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _problem(401, "Missing bearer token", "Authorization header required")
    token = authorization.split(" ", 1)[1]
    result = service.verify(token)
    if isinstance(result, Failure):
        raise _problem(401, "Invalid token", result.error.detail)
    request.state.user = result.value
    return result.value


async def require_posting_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    expected = request.app.state.posting_api_key
    if x_api_key != expected:
        raise _problem(
            401, "Missing or invalid API key", "X-API-Key header required"
        )
