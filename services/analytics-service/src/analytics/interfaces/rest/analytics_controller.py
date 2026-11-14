from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from analytics.application.queryservices.query_application_service import (
    QueryApplicationService,
)
from analytics.domain.model.queries.daily_metrics_query import (
    GetDailyMetricsQuery,
    GetSummaryMetricsQuery,
)
from analytics.domain.model.queries.list_alerts_query import ListAlertsQuery
from analytics.domain.model.queries.list_transactions_query import (
    ListTransactionsQuery,
)
from analytics.domain.model.valueobjects.alert_status import AlertStatus
from analytics.domain.model.valueobjects.decision import Decision
from analytics.domain.model.valueobjects.priority import Priority
from analytics.interfaces.rest.resources.read_resources import (
    AlertResource,
    DailyMetricResource,
    SummaryMetricResource,
    TransactionResource,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _service(request: Request) -> QueryApplicationService:
    return request.app.state.query_application_service


def _422(detail: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={"title": "Invalid query", "detail": detail},
    )


@router.get(
    "/transactions",
    response_model=list[TransactionResource],
    summary="List transactions with filters (Power BI data source)",
)
async def list_transactions(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    decision: Decision | None = Query(default=None),
    country: str | None = Query(default=None, max_length=3),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: QueryApplicationService = Depends(_service),
) -> list[TransactionResource]:
    try:
        query = ListTransactionsQuery(
            date_from=date_from,
            date_to=date_to,
            decision=decision,
            country=country,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise _422(str(exc)) from exc
    dtos = await service.list_transactions(query)
    return [TransactionResource.model_validate(asdict(d)) for d in dtos]


@router.get(
    "/alerts",
    response_model=list[AlertResource],
    summary="List alerts with filters (Power BI data source)",
)
async def list_alerts(
    status: AlertStatus | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: QueryApplicationService = Depends(_service),
) -> list[AlertResource]:
    try:
        query = ListAlertsQuery(
            status=status, priority=priority, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise _422(str(exc)) from exc
    dtos = await service.list_alerts(query)
    return [AlertResource.model_validate(asdict(d)) for d in dtos]


@router.get(
    "/metrics/daily",
    response_model=list[DailyMetricResource],
    summary="Daily metrics for the given range",
)
async def daily_metrics(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    service: QueryApplicationService = Depends(_service),
) -> list[DailyMetricResource]:
    try:
        query = GetDailyMetricsQuery(date_from=date_from, date_to=date_to)
    except ValueError as exc:
        raise _422(str(exc)) from exc
    dtos = await service.daily_metrics(query)
    return [DailyMetricResource.model_validate(asdict(d)) for d in dtos]


@router.get(
    "/metrics/summary",
    response_model=SummaryMetricResource,
    summary="Cumulative summary metrics across the whole dataset",
)
async def summary_metrics(
    service: QueryApplicationService = Depends(_service),
) -> SummaryMetricResource:
    dto = await service.summary_metrics(GetSummaryMetricsQuery())
    return SummaryMetricResource.model_validate(asdict(dto))
