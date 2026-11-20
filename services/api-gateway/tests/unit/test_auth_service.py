from __future__ import annotations

from uuid import UUID

import pytest

from gateway.application.auth_service import (
    AuthService,
    LoginCommand,
    StoredUser,
)
from gateway.infrastructure.security.bcrypt_hasher import BcryptPasswordHasher
from gateway.infrastructure.security.env_user_repository import EnvUserRepository
from gateway.infrastructure.security.jwt_issuer import PyJwtIssuer
from gateway.kernel.application.result import Failure, Success

SECRET = "x" * 32
ANALYST = UUID("11111111-1111-1111-1111-111111111111")


def _service(hashed: str) -> AuthService:
    class StaticRepo:
        def find(self, username: str):
            if username == "kevin":
                return StoredUser("kevin", hashed, ANALYST)
            return None

    return AuthService(
        users=StaticRepo(),
        hasher=BcryptPasswordHasher(),
        issuer=PyJwtIssuer(SECRET, "HS256", 60, "test-issuer"),
    )


def test_login_rejects_unknown_user() -> None:
    svc = _service(BcryptPasswordHasher.hash("secret"))
    result = svc.login(LoginCommand(username="nope", password="secret"))
    assert isinstance(result, Failure)
    assert result.error.code == "unauthorized"


def test_login_rejects_wrong_password() -> None:
    svc = _service(BcryptPasswordHasher.hash("secret"))
    result = svc.login(LoginCommand(username="kevin", password="other"))
    assert isinstance(result, Failure)


def test_login_success_issues_verifiable_token() -> None:
    svc = _service(BcryptPasswordHasher.hash("secret"))
    issued = svc.login(LoginCommand(username="kevin", password="secret"))
    assert isinstance(issued, Success)

    verified = svc.verify(issued.value.access_token)
    assert isinstance(verified, Success)
    assert verified.value.username == "kevin"
    assert verified.value.analyst_id == ANALYST


def test_verify_rejects_tampered_token() -> None:
    svc = _service(BcryptPasswordHasher.hash("secret"))
    issued = svc.login(LoginCommand(username="kevin", password="secret"))
    assert isinstance(issued, Success)
    tampered = issued.value.access_token + "x"
    assert isinstance(svc.verify(tampered), Failure)


def test_env_user_repository_parses_csv() -> None:
    bcrypt_hash = BcryptPasswordHasher.hash("secret")
    csv = f"kevin:{bcrypt_hash}:{ANALYST},jose:{bcrypt_hash}:22222222-2222-2222-2222-222222222222"
    repo = EnvUserRepository(csv)
    assert repo.find("kevin") is not None
    assert repo.find("jose") is not None
    assert repo.find("nobody") is None


@pytest.mark.parametrize("csv", ["", "   ", "malformed"])
def test_env_user_repository_tolerates_malformed(csv: str) -> None:
    repo = EnvUserRepository(csv)
    assert repo.find("whatever") is None
