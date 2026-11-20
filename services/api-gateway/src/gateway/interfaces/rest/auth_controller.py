from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from gateway.application.auth_service import LoginCommand
from gateway.kernel.application.result import Failure

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/token", response_model=TokenResponse)
async def issue_token(body: LoginRequest, request: Request) -> TokenResponse:
    service = request.app.state.auth_service
    result = service.login(LoginCommand(username=body.username, password=body.password))
    if isinstance(result, Failure):
        raise HTTPException(
            status_code=401,
            detail={"title": "Authentication failed", "detail": result.error.detail},
        )
    pair = result.value
    return TokenResponse(access_token=pair.access_token, expires_in=pair.expires_in)
