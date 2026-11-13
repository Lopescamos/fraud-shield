"""create scoring schema tables (scoring_results, model_registry, outbox_events, processed_events)

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
    op.execute("CREATE SCHEMA IF NOT EXISTS scoring")

    op.create_table(
        "scoring_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id_hash", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("rules_score", sa.Integer, nullable=False),
        sa.Column("xgb_probability", sa.Numeric(8, 6), nullable=False),
        sa.Column("iforest_anomaly", sa.Numeric(8, 6), nullable=False),
        sa.Column("degraded_mode", sa.Boolean, nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column(
            "factors",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="scoring",
    )
    op.create_index(
        "ix_scoring_results_transaction_id",
        "scoring_results",
        ["transaction_id"],
        unique=True,
        schema="scoring",
    )
    op.create_index(
        "ix_scoring_results_account_hash_occurred",
        "scoring_results",
        ["account_id_hash", sa.text("occurred_at DESC")],
        schema="scoring",
    )

    op.create_table(
        "model_registry",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("algorithm", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column(
            "metrics",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "trained_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="scoring",
    )
    op.create_index(
        "ix_model_registry_algo_active",
        "model_registry",
        ["algorithm", "is_active"],
        schema="scoring",
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
        schema="scoring",
    )
    op.create_index(
        "ix_scoring_outbox_status_created_at",
        "outbox_events",
        ["status", "created_at"],
        schema="scoring",
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
        schema="scoring",
    )


def downgrade() -> None:
    op.drop_table("processed_events", schema="scoring")
    op.drop_index(
        "ix_scoring_outbox_status_created_at",
        table_name="outbox_events",
        schema="scoring",
    )
    op.drop_table("outbox_events", schema="scoring")
    op.drop_index(
        "ix_model_registry_algo_active",
        table_name="model_registry",
        schema="scoring",
    )
    op.drop_table("model_registry", schema="scoring")
    op.drop_index(
        "ix_scoring_results_account_hash_occurred",
        table_name="scoring_results",
        schema="scoring",
    )
    op.drop_index(
        "ix_scoring_results_transaction_id",
        table_name="scoring_results",
        schema="scoring",
    )
    op.drop_table("scoring_results", schema="scoring")
