from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from scoring.infrastructure.persistence.session import Base


class ScoringResultPersistenceEntity(Base):
    __tablename__ = "scoring_results"
    __table_args__ = (
        Index(
            "ix_scoring_results_transaction_id",
            "transaction_id",
            unique=True,
        ),
        Index(
            "ix_scoring_results_account_hash_occurred",
            "account_id_hash",
            "occurred_at",
        ),
        {"schema": "scoring"},
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    transaction_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    account_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    rules_score: Mapped[int] = mapped_column(Integer, nullable=False)
    xgb_probability: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    iforest_anomaly: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    degraded_mode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    factors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
