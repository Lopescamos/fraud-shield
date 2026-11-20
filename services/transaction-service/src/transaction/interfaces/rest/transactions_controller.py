from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from transaction.application.commandservices.transaction_batch_command_service import (
    TransactionBatchCommandService,
)
from transaction.application.commandservices.transaction_command_service import (
    TransactionCommandService,
)
from transaction.application.queryservices.transaction_query_service import (
    TransactionQueryService,
)
from transaction.domain.model.queries.get_transaction_by_id_query import (
    GetTransactionByIdQuery,
)
from transaction.interfaces.rest.exception_handlers import raise_from_error
from transaction.interfaces.rest.resources.register_batch_transactions_resource import (
    BatchAcceptedResource,
    BatchItemOutcomeResource,
    RegisterBatchTransactionsResource,
)
from transaction.interfaces.rest.resources.register_transaction_resource import (
    RegisterTransactionResource,
)
from transaction.interfaces.rest.resources.transaction_accepted_resource import (
    TransactionAcceptedResource,
)
from transaction.interfaces.rest.resources.transaction_resource import (
    TransactionResource,
)
from transaction.interfaces.rest.transform.register_batch_command_from_resource_assembler import (
    RegisterBatchCommandFromResourceAssembler as BatchRequestMapper,
)
from transaction.interfaces.rest.transform.register_transaction_command_from_resource_assembler import (
    RegisterTransactionCommandFromResourceAssembler as RequestMapper,
)
from transaction.interfaces.rest.transform.transaction_resource_from_entity_assembler import (
    TransactionResourceFromEntityAssembler as ResponseMapper,
)
from transaction.kernel.application.result import Failure

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


def _command_service(request: Request) -> TransactionCommandService:
    return request.app.state.transaction_command_service


def _batch_command_service(request: Request) -> TransactionBatchCommandService:
    return request.app.state.transaction_batch_command_service


def _query_service(request: Request) -> TransactionQueryService:
    return request.app.state.transaction_query_service


@router.post(
    "",
    response_model=TransactionAcceptedResource,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register a transaction for risk evaluation",
)
async def register_transaction(
    resource: RegisterTransactionResource,
    service: TransactionCommandService = Depends(_command_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> TransactionAcceptedResource:
    command = RequestMapper.to_command(resource)
    result = await service.handle(command, idempotency_key=idempotency_key)
    if isinstance(result, Failure):
        raise_from_error(result.error)
    return TransactionAcceptedResource(transaction_id=result.value)


@router.post(
    "/batch",
    response_model=BatchAcceptedResource,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register up to 500 transactions in one call (US-02)",
)
async def register_batch_transactions(
    resource: RegisterBatchTransactionsResource,
    service: TransactionBatchCommandService = Depends(_batch_command_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> BatchAcceptedResource:
    command = BatchRequestMapper.to_command(resource)
    outcomes = await service.handle(command, idempotency_key=idempotency_key)
    accepted = sum(1 for o in outcomes if o.ok)
    rejected = sum(1 for o in outcomes if not o.ok)
    return BatchAcceptedResource(
        outcomes=[
            BatchItemOutcomeResource(
                index=o.index,
                transaction_id=o.transaction_id,
                error=(
                    None
                    if o.error is None
                    else {
                        "code": o.error.code,
                        "title": o.error.title,
                        "detail": o.error.detail,
                    }
                ),
            )
            for o in outcomes
        ],
        accepted=accepted,
        rejected=rejected,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResource,
    summary="Get a transaction by its id",
)
async def get_transaction(
    transaction_id: UUID,
    service: TransactionQueryService = Depends(_query_service),
) -> TransactionResource:
    tx = await service.handle(GetTransactionByIdQuery(transaction_id=transaction_id))
    if tx is None:
        raise HTTPException(
            status_code=404,
            detail={
                "title": "Transaction not found",
                "detail": f"Transaction with id '{transaction_id}' does not exist",
            },
        )
    return ResponseMapper.to_resource(tx)
