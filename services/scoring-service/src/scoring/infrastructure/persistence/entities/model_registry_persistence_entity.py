from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from scoring.infrastructure.persistence.session import Base


class ModelRegistryPersistenceEntity(Base):
    __tablename__ = "model_registry"
    __table_args__ = (
        Index(
            "ix_model_registry_algo_active",
            "algorithm",
            "is_active",
        ),
        {"schema": "scoring"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
