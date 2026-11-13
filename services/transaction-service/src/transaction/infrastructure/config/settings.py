from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TRANSACTION_")

    database_url: str = (
        "postgresql+asyncpg://tx_user:dev_tx@localhost:5432/fraudshield"
    )
    kafka_bootstrap_servers: str = "localhost:9092"
    log_level: str = "INFO"
    outbox_relay_enabled: bool = False
    outbox_relay_interval_ms: int = 500
