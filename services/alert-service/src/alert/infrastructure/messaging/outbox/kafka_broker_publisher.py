from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class KafkaBrokerPublisher:
    """Pushes a serialized envelope to Kafka. Used only by the
    OutboxRelay. Imports aiokafka lazily."""

    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: Any | None = None

    async def start(self) -> None:
        from aiokafka import AIOKafkaProducer

        self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap_servers)
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(self, channel: str, key: str, envelope: dict) -> None:
        if self._producer is None:
            raise RuntimeError("[KafkaBrokerPublisher] start() was not called")
        await self._producer.send_and_wait(
            channel,
            value=json.dumps(envelope).encode("utf-8"),
            key=key.encode("utf-8"),
        )
