"""create tx schema tables (transactions, outbox_events, idempotency_keys)

Revision ID: 00000000000001
Revises:
Create Date: 2026-11-12
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
    op.execute("CREATE SCHEMA IF NOT EXISTS tx")

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id_hash", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        schema="tx",
    )
    op.create_index(
        "ix_transactions_account_hash_occurred",
        "transactions",
        ["account_id_hash", sa.text("occurred_at DESC")],
        schema="tx",
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
        sa.Column("message_key", sa.String(length=64), nullable=False),
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
        schema="tx",
    )
    op.create_index(
        "ix_outbox_events_status_created_at",
        "outbox_events",
        ["status", "created_at"],
        schema="tx",
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=80), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="tx",
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys", schema="tx")
    op.drop_index("ix_outbox_events_status_created_at", table_name="outbox_events", schema="tx")
    op.drop_table("outbox_events", schema="tx")
    op.drop_index(
        "ix_transactions_account_hash_occurred",
        table_name="transactions",
        schema="tx",
    )
    op.drop_table("transactions", schema="tx")
