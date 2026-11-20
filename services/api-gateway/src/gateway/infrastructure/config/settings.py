from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="GATEWAY_")

    log_level: str = "INFO"

    jwt_secret: str = "change-me-dev-only-at-least-32-chars-long"
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 3600
    jwt_issuer: str = "fraudshield-api-gateway"

    # CSV "username:bcrypt_hash:analyst_uuid"
    users: str = ""

    posting_api_key: str = "dev-posting-key-change-me"

    transaction_service_url: str = "http://localhost:8001"
    scoring_service_url: str = "http://localhost:8002"
    alert_service_url: str = "http://localhost:8003"
    analytics_service_url: str = "http://localhost:8004"
    analytics_api_key: str = "dev-powerbi-key-change-me"

    http_timeout_seconds: int = 10
