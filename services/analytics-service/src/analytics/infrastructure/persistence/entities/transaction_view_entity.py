from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from analytics.infrastructure.persistence.session import Base


class TransactionViewEntity(Base):
    __tablename__ = "transactions_view"
    __table_args__ = (
        Index("ix_tx_view_occurred_at", "occurred_at"),
        Index("ix_tx_view_decision", "decision"),
        Index("ix_tx_view_country", "country"),
        {"schema": "analytics"},
    )

    transaction_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True
    )
    account_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    country: Mapped[str | None] = mapped_column(String(3), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    degraded_mode: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
