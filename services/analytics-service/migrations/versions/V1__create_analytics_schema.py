"""create analytics schema tables (transactions_view, alerts_view, processed_events)

Revision ID: 00000000000001
Revises:
Create Date: 2026-11-14
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
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    op.create_table(
        "transactions_view",
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id_hash", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("country", sa.String(length=3), nullable=True),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.Integer, nullable=True),
        sa.Column("level", sa.String(length=16), nullable=True),
        sa.Column("decision", sa.String(length=16), nullable=True),
        sa.Column("model_version", sa.String(length=80), nullable=True),
        sa.Column("degraded_mode", sa.Boolean, nullable=True),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
        schema="analytics",
    )
    op.create_index(
        "ix_tx_view_occurred_at",
        "transactions_view",
        [sa.text("occurred_at DESC")],
        schema="analytics",
    )
    op.create_index(
        "ix_tx_view_decision",
        "transactions_view",
        ["decision"],
        schema="analytics",
    )
    op.create_index(
        "ix_tx_view_country",
        "transactions_view",
        ["country"],
        schema="analytics",
    )

    op.create_table(
        "alerts_view",
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id_hash", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analyst_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        schema="analytics",
    )
    op.create_index(
        "ix_alert_view_opened_at",
        "alerts_view",
        [sa.text("opened_at DESC")],
        schema="analytics",
    )
    op.create_index(
        "ix_alert_view_status",
        "alerts_view",
        ["status"],
        schema="analytics",
    )
    op.create_index(
        "ix_alert_view_priority",
        "alerts_view",
        ["priority"],
        schema="analytics",
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
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_table("processed_events", schema="analytics")
    op.drop_index(
        "ix_alert_view_priority", table_name="alerts_view", schema="analytics"
    )
    op.drop_index(
        "ix_alert_view_status", table_name="alerts_view", schema="analytics"
    )
    op.drop_index(
        "ix_alert_view_opened_at", table_name="alerts_view", schema="analytics"
    )
    op.drop_table("alerts_view", schema="analytics")
    op.drop_index(
        "ix_tx_view_country", table_name="transactions_view", schema="analytics"
    )
    op.drop_index(
        "ix_tx_view_decision", table_name="transactions_view", schema="analytics"
    )
    op.drop_index(
        "ix_tx_view_occurred_at", table_name="transactions_view", schema="analytics"
    )
    op.drop_table("transactions_view", schema="analytics")
