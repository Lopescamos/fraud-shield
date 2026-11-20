from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from gateway.infrastructure.config.settings import Settings
from gateway.infrastructure.security.bcrypt_hasher import BcryptPasswordHasher
from gateway.main import create_app

ANALYST = UUID("11111111-1111-1111-1111-111111111111")
SECRET = "a-very-dev-only-secret-at-least-32-chars"


@pytest.fixture
def valid_settings() -> Settings:
    bcrypt_hash = BcryptPasswordHasher.hash("secret")
    return Settings(
        jwt_secret=SECRET,
        jwt_ttl_seconds=60,
        users=f"kevin:{bcrypt_hash}:{ANALYST}",
        posting_api_key="posting-key",
        transaction_service_url="http://tx",
        scoring_service_url="http://sc",
        alert_service_url="http://al",
        analytics_service_url="http://an",
        analytics_api_key="analytics-internal-key",
    )


class _StubProxy:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def forward(self, **kwargs):
        from fastapi import Response

        self.calls.append(kwargs)
        return Response(content=b'{"ok":true}', status_code=200,
                        media_type="application/json")


@pytest.mark.asyncio
async def test_health_is_public(valid_settings) -> None:
    app = create_app(valid_settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_issues_bearer_token(valid_settings) -> None:
    app = create_app(valid_settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.post(
            "/auth/token", json={"username": "kevin", "password": "secret"}
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 60
    assert body["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(valid_settings) -> None:
    app = create_app(valid_settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.post(
            "/auth/token", json={"username": "kevin", "password": "wrong"}
        )
    assert resp.status_code == 401


async def _login(client: AsyncClient) -> str:
    resp = await client.post(
        "/auth/token", json={"username": "kevin", "password": "secret"}
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_get_alert_requires_jwt(valid_settings) -> None:
    app = create_app(valid_settings)
    app.state.proxy_client = _StubProxy()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get(f"/api/v1/alerts/{uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_alert_proxies_with_valid_jwt(valid_settings) -> None:
    app = create_app(valid_settings)
    proxy = _StubProxy()
    app.state.proxy_client = proxy
    alert_id = uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        token = await _login(c)
        resp = await c.get(
            f"/api/v1/alerts/{alert_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    call = proxy.calls[0]
    assert call["method"] == "GET"
    assert call["base_url"] == "http://al"
    assert call["path"] == f"/api/v1/alerts/{alert_id}"


@pytest.mark.asyncio
async def test_post_transaction_requires_posting_api_key(valid_settings) -> None:
    app = create_app(valid_settings)
    proxy = _StubProxy()
    app.state.proxy_client = proxy
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp_missing = await c.post("/api/v1/transactions", json={"a": 1})
        resp_ok = await c.post(
            "/api/v1/transactions",
            json={"a": 1},
            headers={"X-API-Key": "posting-key"},
        )
    assert resp_missing.status_code == 401
    assert resp_ok.status_code == 200
    assert proxy.calls[0]["body"] == {"a": 1}


@pytest.mark.asyncio
async def test_assign_alert_injects_analyst_id_from_jwt(valid_settings) -> None:
    app = create_app(valid_settings)
    proxy = _StubProxy()
    app.state.proxy_client = proxy
    alert_id = uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        token = await _login(c)
        resp = await c.patch(
            f"/api/v1/alerts/{alert_id}/assign",
            json={"analyst_id": str(uuid4())},  # Should be ignored.
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    forwarded_body = proxy.calls[0]["body"]
    assert forwarded_body["analyst_id"] == str(ANALYST)


@pytest.mark.asyncio
async def test_analytics_proxy_injects_api_key(valid_settings) -> None:
    app = create_app(valid_settings)
    proxy = _StubProxy()
    app.state.proxy_client = proxy
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        token = await _login(c)
        resp = await c.get(
            "/analytics/transactions?limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    call = proxy.calls[0]
    assert call["headers"]["X-API-Key"] == "analytics-internal-key"
    assert call["query"] == {"limit": "10"}
