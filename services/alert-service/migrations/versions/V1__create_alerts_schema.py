"""create alerts schema tables (alerts, outbox_events, processed_events)

Revision ID: 00000000000001
Revises:
Create Date: 2026-11-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "00000000000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS alerts")

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "scoring_result_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("account_id_hash", sa.String(length=64), nullable=False),
        sa.Column("risk_score", sa.Integer, nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "factors",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("analyst_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="alerts",
    )
    op.create_index(
        "ix_alerts_transaction_id",
        "alerts",
        ["transaction_id"],
        unique=True,
        schema="alerts",
    )
    op.create_index(
        "ix_alerts_status_opened_at",
        "alerts",
        ["status", sa.text("opened_at DESC")],
        schema="alerts",
    )
    op.create_index(
        "ix_alerts_priority_opened_at",
        "alerts",
        ["priority", sa.text("opened_at DESC")],
        schema="alerts",
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("message_key", sa.String(length=80), nullable=False),
        sa.Column("message_type", sa.String(length=80), nullable=False),
        sa.Column("schema_version", sa.SmallInteger, nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="alerts",
    )
    op.create_index(
        "ix_alerts_outbox_status_created_at",
        "outbox_events",
        ["status", "created_at"],
        schema="alerts",
    )

    op.create_table(
        "processed_events",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("consumer_group", sa.String(length=80), primary_key=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="alerts",
    )


def downgrade() -> None:
    op.drop_table("processed_events", schema="alerts")
    op.drop_index(
        "ix_alerts_outbox_status_created_at",
        table_name="outbox_events",
        schema="alerts",
    )
    op.drop_table("outbox_events", schema="alerts")
    op.drop_index("ix_alerts_priority_opened_at", table_name="alerts", schema="alerts")
    op.drop_index("ix_alerts_status_opened_at", table_name="alerts", schema="alerts")
    op.drop_index("ix_alerts_transaction_id", table_name="alerts", schema="alerts")
    op.drop_table("alerts", schema="alerts")
