from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from gateway.domain.model.authenticated_user import AuthenticatedUser
from gateway.kernel.application.result import ApplicationError, Result


@dataclass(frozen=True, slots=True)
class LoginCommand:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    expires_in: int


class PasswordHasher(Protocol):
    def verify(self, password: str, hashed: str) -> bool: ...


class TokenIssuer(Protocol):
    def issue(self, user: AuthenticatedUser) -> TokenPair: ...
    def verify(self, token: str) -> AuthenticatedUser: ...


@dataclass(frozen=True, slots=True)
class StoredUser:
    username: str
    hashed_password: str
    analyst_id: UUID


class UserRepository(Protocol):
    def find(self, username: str) -> StoredUser | None: ...


class AuthService:
    """Owns the login use case. The adapters (bcrypt, PyJWT, env-based
    repo) live in ``infrastructure/security`` behind these ports."""

    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        issuer: TokenIssuer,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._issuer = issuer

    def login(self, command: LoginCommand) -> Result[TokenPair, ApplicationError]:
        from gateway.kernel.application.result import Failure, Success

        user = self._users.find(command.username)
        if user is None or not self._hasher.verify(
            command.password, user.hashed_password
        ):
            return Failure(
                ApplicationError.unauthorized("invalid username or password")
            )
        token = self._issuer.issue(
            AuthenticatedUser(username=user.username, analyst_id=user.analyst_id)
        )
        return Success(token)

    def verify(self, token: str) -> Result[AuthenticatedUser, ApplicationError]:
        from gateway.kernel.application.result import Failure, Success

        try:
            user = self._issuer.verify(token)
        except Exception as exc:  # pragma: no cover - adapter translates
            return Failure(ApplicationError.unauthorized(str(exc)))
        return Success(user)
