from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from scoring.application.commandservices.scoring_application_service import (
    ScoringApplicationService,
)
from scoring.application.queryservices.scoring_result_query_service import (
    ScoringResultQueryService,
)
from scoring.domain.model.queries.get_scoring_result_by_id_query import (
    GetScoringResultByIdQuery,
)
from scoring.interfaces.rest.exception_handlers import raise_from_error
from scoring.interfaces.rest.resources.score_transaction_resource import (
    ScoreTransactionResource,
)
from scoring.interfaces.rest.resources.scoring_accepted_resource import (
    ScoringAcceptedResource,
)
from scoring.interfaces.rest.resources.scoring_result_resource import (
    ScoringResultResource,
)
from scoring.interfaces.rest.transform.score_transaction_command_from_resource_assembler import (
    ScoreTransactionCommandFromResourceAssembler as RequestMapper,
)
from scoring.interfaces.rest.transform.scoring_result_resource_from_entity_assembler import (
    ScoringResultResourceFromEntityAssembler as ResponseMapper,
)
from scoring.kernel.application.result import Failure

router = APIRouter(prefix="/api/v1/scores", tags=["Scores"])


def _command_service(request: Request) -> ScoringApplicationService:
    return request.app.state.scoring_application_service


def _query_service(request: Request) -> ScoringResultQueryService:
    return request.app.state.scoring_result_query_service


@router.post(
    "",
    response_model=ScoringAcceptedResource,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Score a transaction (manual ingestion while Kafka is down)",
)
async def score_transaction(
    resource: ScoreTransactionResource,
    service: ScoringApplicationService = Depends(_command_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ScoringAcceptedResource:
    command = RequestMapper.to_command(resource)
    result = await service.handle(command, idempotency_key=idempotency_key)
    if isinstance(result, Failure):
        raise_from_error(result.error)
    return ScoringAcceptedResource(scoring_result_id=result.value)


@router.get(
    "/{scoring_result_id}",
    response_model=ScoringResultResource,
    summary="Get a scoring result by its id",
)
async def get_scoring_result(
    scoring_result_id: UUID,
    service: ScoringResultQueryService = Depends(_query_service),
) -> ScoringResultResource:
    result = await service.handle(
        GetScoringResultByIdQuery(scoring_result_id=scoring_result_id)
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "title": "Scoring result not found",
                "detail": f"Scoring result with id '{scoring_result_id}' does not exist",
            },
        )
    return ResponseMapper.to_resource(result)
