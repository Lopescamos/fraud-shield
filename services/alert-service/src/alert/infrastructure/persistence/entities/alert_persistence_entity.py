from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from alert.infrastructure.persistence.session import Base


class AlertPersistenceEntity(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index(
            "ix_alerts_transaction_id",
            "transaction_id",
            unique=True,
        ),
        Index("ix_alerts_status_opened_at", "status", "opened_at"),
        Index("ix_alerts_priority_opened_at", "priority", "opened_at"),
        {"schema": "alerts"},
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    transaction_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    scoring_result_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False
    )
    account_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    factors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    analyst_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )
