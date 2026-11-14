from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from analytics.application.dto.projection_input import (
    AlertRaisedInput,
    AlertResolvedInput,
    TransactionReceivedInput,
    TransactionScoredInput,
)
from analytics.domain.repositories.analytics_projection_repository import (
    AnalyticsProjectionRepository,
)
from analytics.kernel.application.result import (
    ApplicationError,
    Failure,
    Result,
    Success,
)
from analytics.kernel.messaging.idempotent_executor import (
    IdempotentExecutor,
    ProcessedEventStore,
)

logger = logging.getLogger(__name__)


ProjectionBuilder = Callable[[Any], AnalyticsProjectionRepository]
StoreBuilder = Callable[[Any], ProcessedEventStore]


class ProjectionApplicationServiceImpl:
    """
    Fans each integration event into one UPSERT on the projection
    repository. The ``IdempotentExecutor`` writes its marker in the
    same session, so a retried message is a no-op.
    """

    def __init__(
        self,
        session_factory: Any,
        projection_builder: ProjectionBuilder,
        store_builder: StoreBuilder,
    ) -> None:
        self._session_factory = session_factory
        self._projection_builder = projection_builder
        self._store_builder = store_builder

    async def on_transaction_received(
        self, input_: TransactionReceivedInput, consumer_group: str
    ) -> Result[None, ApplicationError]:
        async def op(repo: AnalyticsProjectionRepository) -> None:
            await repo.upsert_transaction_received(
                transaction_id=input_.transaction_id,
                account_id_hash=input_.account_id_hash,
                amount=input_.amount,
                currency=input_.currency,
                channel=input_.channel,
                country=input_.country,
                device_id=input_.device_id,
                occurred_at=input_.occurred_at,
                received_at=input_.received_at,
            )

        return await self._run(input_.message_id, consumer_group, op, "transaction-received")

    async def on_transaction_scored(
        self, input_: TransactionScoredInput, consumer_group: str
    ) -> Result[None, ApplicationError]:
        async def op(repo: AnalyticsProjectionRepository) -> None:
            await repo.upsert_transaction_scored(
                transaction_id=input_.transaction_id,
                account_id_hash=input_.account_id_hash,
                risk_score=input_.risk_score,
                level=input_.level,
                decision=input_.decision,
                model_version=input_.model_version,
                degraded_mode=input_.degraded_mode,
                scored_at=input_.scored_at,
            )

        return await self._run(input_.message_id, consumer_group, op, "transaction-scored")

    async def on_alert_raised(
        self, input_: AlertRaisedInput, consumer_group: str
    ) -> Result[None, ApplicationError]:
        async def op(repo: AnalyticsProjectionRepository) -> None:
            await repo.upsert_alert_raised(
                alert_id=input_.alert_id,
                transaction_id=input_.transaction_id,
                account_id_hash=input_.account_id_hash,
                severity=input_.severity,
                score=input_.score,
                level=input_.level,
                opened_at=input_.opened_at,
            )

        return await self._run(input_.message_id, consumer_group, op, "alert-raised")

    async def on_alert_resolved(
        self, input_: AlertResolvedInput, consumer_group: str
    ) -> Result[None, ApplicationError]:
        async def op(repo: AnalyticsProjectionRepository) -> None:
            await repo.upsert_alert_resolved(
                alert_id=input_.alert_id,
                transaction_id=input_.transaction_id,
                previous_status=input_.previous_status,
                new_status=input_.new_status,
                analyst_id=input_.analyst_id,
                reason=input_.reason,
                closed_at=input_.closed_at,
            )

        return await self._run(input_.message_id, consumer_group, op, "alert-resolved")

    async def _run(
        self,
        message_id,
        consumer_group: str,
        operation,
        label: str,
    ) -> Result[None, ApplicationError]:
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    repo = self._projection_builder(session)
                    store = self._store_builder(session)
                    executor = IdempotentExecutor(store)

                    async def _op() -> None:
                        await operation(repo)

                    await executor.run_once(
                        message_id=message_id,
                        group=consumer_group,
                        operation=_op,
                    )
        except Exception as exc:
            logger.exception("projection-failed", extra={"label": label})
            return Failure(ApplicationError.unexpected(f"project-{label}", str(exc)))
        return Success(None)
