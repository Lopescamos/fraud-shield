from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from scoring.application.internal.commandservices.scoring_application_service_impl import (
    ScoringApplicationServiceImpl,
    ScoringWeights,
)
from scoring.application.internal.eventhandlers.scoring_result_registered_event_handler import (
    ScoringResultRegisteredEventHandler,
)
from scoring.application.internal.queryservices.scoring_result_query_service_impl import (
    ScoringResultQueryServiceImpl,
)
from scoring.domain.model.events.scoring_result_registered_event import (
    ScoringResultRegisteredEvent,
)
from scoring.infrastructure.config.settings import Settings
from scoring.infrastructure.logging import configure as configure_logging
from scoring.infrastructure.messaging.outbox.outbox_message_publisher import (
    OutboxMessagePublisher,
)
from scoring.infrastructure.ml.isolation_forest_risk_model import (
    IsolationForestRiskModel,
)
from scoring.infrastructure.ml.shap_explainer import ShapExplainer
from scoring.infrastructure.ml.xgboost_risk_model import XGBoostRiskModel
from scoring.infrastructure.persistence.repositories.scoring_result_repository_impl import (
    ScoringResultRepositoryImpl,
)
from scoring.infrastructure.persistence.session import (
    build_engine,
    build_session_factory,
)
from scoring.infrastructure.rules.catalog_rule_engine import CatalogRuleEngine
from scoring.infrastructure.rules.yaml_rule_catalog import YamlRuleCatalog
from scoring.interfaces.rest import exception_handlers
from scoring.interfaces.rest.health_controller import router as health_router
from scoring.interfaces.rest.scores_controller import router as scores_router
from scoring.kernel.domain.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)


def _build_repository_builder() -> Any:
    def repository_builder(session: Any) -> ScoringResultRepositoryImpl:
        publisher = OutboxMessagePublisher(session)
        handler = ScoringResultRegisteredEventHandler(publisher)
        dispatcher = EventDispatcher()
        dispatcher.register(
            ScoringResultRegisteredEvent, handler.on_scoring_result_registered
        )
        return ScoringResultRepositoryImpl(session, dispatcher)

    return repository_builder


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    repository_builder = _build_repository_builder()

    rules_path = Path(settings.rules_path)
    rule_engine = CatalogRuleEngine(YamlRuleCatalog(rules_path))

    xgb_model = XGBoostRiskModel.load_or_degrade(
        settings.xgb_model_path or None, settings.model_version
    )
    iforest_model = IsolationForestRiskModel.load_or_degrade(
        settings.iforest_model_path or None, settings.model_version
    )
    explainer = ShapExplainer.from_booster(
        getattr(xgb_model, "_booster", None)
    )

    if not (xgb_model.is_available() and iforest_model.is_available()):
        logger.warning(
            "scoring-service-degraded",
            extra={
                "xgb_available": xgb_model.is_available(),
                "iforest_available": iforest_model.is_available(),
            },
        )

    weights = ScoringWeights(
        rules=settings.weight_rules,
        xgb=settings.weight_xgb,
        iforest=settings.weight_iforest,
    )

    command_service = ScoringApplicationServiceImpl(
        session_factory=session_factory,
        repository_builder=repository_builder,
        rule_engine=rule_engine,
        xgb_model=xgb_model,
        iforest_model=iforest_model,
        explainer=explainer,
        weights=weights,
    )
    query_service = ScoringResultQueryServiceImpl(
        session_factory=session_factory,
        repository_builder=repository_builder,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="Scoring Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.scoring_application_service = command_service
    app.state.scoring_result_query_service = query_service

    exception_handlers.register(app)
    app.include_router(health_router)
    app.include_router(scores_router)

    return app


app = create_app()
