from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from alert.application.commandservices.alert_application_service import (
    AlertApplicationService,
)
from alert.application.queryservices.alert_query_service import AlertQueryService
from alert.domain.model.commands.assign_alert_command import AssignAlertCommand
from alert.domain.model.commands.dismiss_alert_command import DismissAlertCommand
from alert.domain.model.commands.resolve_alert_command import ResolveAlertCommand
from alert.domain.model.queries.get_alert_by_id_query import GetAlertByIdQuery
from alert.domain.model.queries.list_alerts_query import ListAlertsQuery
from alert.domain.model.valueobjects.alert_status import AlertStatus
from alert.domain.model.valueobjects.priority import Priority
from alert.interfaces.rest.exception_handlers import raise_from_error
from alert.interfaces.rest.resources.alert_action_resources import (
    AlertMutationResponse,
    AssignAlertRequest,
    DismissAlertRequest,
    ResolveAlertRequest,
)
from alert.interfaces.rest.resources.alert_resource import AlertResource
from alert.interfaces.rest.transform.alert_resource_from_entity_assembler import (
    AlertResourceFromEntityAssembler as ResponseMapper,
)
from alert.kernel.application.result import Failure

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


def _command_service(request: Request) -> AlertApplicationService:
    return request.app.state.alert_application_service


def _query_service(request: Request) -> AlertQueryService:
    return request.app.state.alert_query_service


@router.get(
    "",
    response_model=list[AlertResource],
    summary="List alerts with filters and pagination",
)
async def list_alerts(
    status: AlertStatus | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: AlertQueryService = Depends(_query_service),
) -> list[AlertResource]:
    try:
        query = ListAlertsQuery(
            status=status, priority=priority, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"title": "Invalid list query", "detail": str(exc)},
        ) from exc

    alerts = await service.list(query)
    return [ResponseMapper.to_resource(a) for a in alerts]


@router.get(
    "/{alert_id}",
    response_model=AlertResource,
    summary="Get an alert by its id",
)
async def get_alert(
    alert_id: UUID,
    service: AlertQueryService = Depends(_query_service),
) -> AlertResource:
    alert = await service.get_by_id(GetAlertByIdQuery(alert_id=alert_id))
    if alert is None:
        raise HTTPException(
            status_code=404,
            detail={
                "title": "Alert not found",
                "detail": f"Alert with id '{alert_id}' does not exist",
            },
        )
    return ResponseMapper.to_resource(alert)


@router.patch(
    "/{alert_id}/assign",
    response_model=AlertMutationResponse,
    summary="Assign an open alert to an analyst",
)
async def assign_alert(
    alert_id: UUID,
    body: AssignAlertRequest,
    service: AlertApplicationService = Depends(_command_service),
) -> AlertMutationResponse:
    result = await service.assign(
        AssignAlertCommand(alert_id=alert_id, analyst_id=body.analyst_id)
    )
    if isinstance(result, Failure):
        raise_from_error(result.error)
    return AlertMutationResponse(alert_id=result.value)


@router.patch(
    "/{alert_id}/resolve",
    response_model=AlertMutationResponse,
    summary="Resolve an in-review alert",
)
async def resolve_alert(
    alert_id: UUID,
    body: ResolveAlertRequest,
    service: AlertApplicationService = Depends(_command_service),
) -> AlertMutationResponse:
    result = await service.resolve(
        ResolveAlertCommand(
            alert_id=alert_id, resolution_notes=body.resolution_notes
        )
    )
    if isinstance(result, Failure):
        raise_from_error(result.error)
    return AlertMutationResponse(alert_id=result.value)


@router.patch(
    "/{alert_id}/dismiss",
    response_model=AlertMutationResponse,
    summary="Dismiss an in-review alert as a false positive",
)
async def dismiss_alert(
    alert_id: UUID,
    body: DismissAlertRequest,
    service: AlertApplicationService = Depends(_command_service),
) -> AlertMutationResponse:
    result = await service.dismiss(
        DismissAlertCommand(alert_id=alert_id, reason=body.reason)
    )
    if isinstance(result, Failure):
        raise_from_error(result.error)
    return AlertMutationResponse(alert_id=result.value)
