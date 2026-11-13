from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALERT_")

    database_url: str = (
        "postgresql+asyncpg://alerts_user:dev_alerts@localhost:5432/fraudshield"
    )
    kafka_bootstrap_servers: str = "localhost:9092"
    log_level: str = "INFO"
    outbox_relay_enabled: bool = False
    outbox_relay_interval_ms: int = 500
    consumer_enabled: bool = False
    consumer_topic: str = "transactions.scored.v1"
    consumer_group: str = "alert.raise-on-scored"
