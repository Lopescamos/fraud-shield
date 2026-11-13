from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from scoring.infrastructure.persistence.session import Base


class ProcessedEventPersistenceEntity(Base):
    """
    Idempotency marker for the Kafka consumer. Keyed by (message_id,
    consumer_group) so the same event re-delivered to the same group is
    skipped, but can be re-processed by a different group.
    """

    __tablename__ = "processed_events"
    __table_args__ = {"schema": "scoring"}

    message_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    consumer_group: Mapped[str] = mapped_column(String(80), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
