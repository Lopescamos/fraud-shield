from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from analytics.infrastructure.persistence.session import Base


class AlertViewEntity(Base):
    __tablename__ = "alerts_view"
    __table_args__ = (
        Index("ix_alert_view_opened_at", "opened_at"),
        Index("ix_alert_view_status", "status"),
        Index("ix_alert_view_priority", "priority"),
        {"schema": "analytics"},
    )

    alert_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    transaction_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    account_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    analyst_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
