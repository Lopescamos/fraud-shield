from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SCORING_")

    database_url: str = (
        "postgresql+asyncpg://scoring_user:dev_scoring@localhost:5432/fraudshield"
    )
    kafka_bootstrap_servers: str = "localhost:9092"
    log_level: str = "INFO"
    outbox_relay_enabled: bool = False
    outbox_relay_interval_ms: int = 500
    consumer_enabled: bool = False
    consumer_topic: str = "transactions.received.v1"
    consumer_group: str = "scoring.assess-transaction"
    rules_path: str = "src/scoring/infrastructure/ml/rules.yaml"
    xgb_model_path: str = ""
    iforest_model_path: str = ""
    model_version: str = "unknown"
    weight_rules: float = 0.4
    weight_xgb: float = 0.4
    weight_iforest: float = 0.2
