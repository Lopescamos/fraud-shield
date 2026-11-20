from __future__ import annotations

import time
from uuid import UUID

import jwt

from gateway.application.auth_service import TokenIssuer, TokenPair
from gateway.domain.model.authenticated_user import AuthenticatedUser


class PyJwtIssuer(TokenIssuer):
    def __init__(
        self, secret: str, algorithm: str, ttl_seconds: int, issuer: str
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = ttl_seconds
        self._issuer = issuer

    def issue(self, user: AuthenticatedUser) -> TokenPair:
        now = int(time.time())
        claims = {
            "iss": self._issuer,
            "sub": user.username,
            "analyst_id": str(user.analyst_id),
            "iat": now,
            "exp": now + self._ttl,
        }
        token = jwt.encode(claims, self._secret, algorithm=self._algorithm)
        return TokenPair(access_token=token, expires_in=self._ttl)

    def verify(self, token: str) -> AuthenticatedUser:
        claims = jwt.decode(
            token,
            self._secret,
            algorithms=[self._algorithm],
            issuer=self._issuer,
            options={"require": ["exp", "iat", "sub", "analyst_id"]},
        )
        return AuthenticatedUser(
            username=str(claims["sub"]),
            analyst_id=UUID(str(claims["analyst_id"])),
        )
