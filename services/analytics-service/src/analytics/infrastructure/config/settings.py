from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ANALYTICS_")

    database_url: str = (
        "postgresql+asyncpg://analytics_user:dev_analytics@localhost:5432/fraudshield"
    )
    kafka_bootstrap_servers: str = "localhost:9092"
    log_level: str = "INFO"
    consumer_enabled: bool = False
    consumer_group: str = "analytics.ingest"
    # CSV so a few comma-separated keys fit in a single env var.
    api_keys: str = "dev-powerbi-key-change-me"

    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}
