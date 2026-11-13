"""Channel, consumer-group and DLQ names used across the system."""

# Channels (Kafka topics).
TRANSACTIONS_RECEIVED_V1 = "transactions.received.v1"
TRANSACTIONS_SCORED_V1 = "transactions.scored.v1"
ALERTS_RAISED_V1 = "alerts.raised.v1"
ALERTS_RESOLVED_V1 = "alerts.resolved.v1"

# Consumer groups.
SCORING_ASSESS_TRANSACTION = "scoring.assess-transaction"
ALERT_RAISE_ON_SCORED = "alert.raise-on-scored"
ANALYTICS_INGEST_RECEIVED = "analytics.ingest-received"
ANALYTICS_INGEST_SCORED = "analytics.ingest-scored"
ANALYTICS_INGEST_ALERTS = "analytics.ingest-alerts"


def dlq_of(group: str) -> str:
    """Return the DLQ name for a consumer group."""
    return f"{group}.dlq"
