from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from transaction.infrastructure.persistence.session import Base


class IdempotencyKeyPersistenceEntity(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = {"schema": "tx"}

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    transaction_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
