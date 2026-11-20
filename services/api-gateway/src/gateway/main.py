from __future__ import annotations

import logging

from fastapi import FastAPI

from gateway.application.auth_service import AuthService
from gateway.infrastructure.config.settings import Settings
from gateway.infrastructure.http.proxy_client import ProxyClient
from gateway.infrastructure.security.bcrypt_hasher import BcryptPasswordHasher
from gateway.infrastructure.security.env_user_repository import EnvUserRepository
from gateway.infrastructure.security.jwt_issuer import PyJwtIssuer
from gateway.interfaces.rest import exception_handlers
from gateway.interfaces.rest.auth_controller import router as auth_router
from gateway.interfaces.rest.health_controller import router as health_router
from gateway.interfaces.rest.proxy_router import router as proxy_router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=settings.log_level)

    issuer = PyJwtIssuer(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        ttl_seconds=settings.jwt_ttl_seconds,
        issuer=settings.jwt_issuer,
    )
    users = EnvUserRepository(settings.users)
    hasher = BcryptPasswordHasher()
    auth_service = AuthService(users=users, hasher=hasher, issuer=issuer)

    proxy = ProxyClient(timeout_seconds=settings.http_timeout_seconds)

    app = FastAPI(title="FraudShield API Gateway", version="0.1.0")
    app.state.auth_service = auth_service
    app.state.proxy_client = proxy
    app.state.posting_api_key = settings.posting_api_key
    app.state.transaction_service_url = settings.transaction_service_url
    app.state.scoring_service_url = settings.scoring_service_url
    app.state.alert_service_url = settings.alert_service_url
    app.state.analytics_service_url = settings.analytics_service_url
    app.state.analytics_api_key = settings.analytics_api_key

    exception_handlers.register(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(proxy_router)

    return app


app = create_app()
