from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from alert.application.internal.commandservices.alert_application_service_impl import (
    AlertApplicationServiceImpl,
)
from alert.application.internal.eventhandlers.alert_raised_event_handler import (
    AlertRaisedEventHandler,
)
from alert.application.internal.eventhandlers.alert_resolved_event_handler import (
    AlertResolvedEventHandler,
)
from alert.application.internal.queryservices.alert_query_service_impl import (
    AlertQueryServiceImpl,
)
from alert.domain.model.events.alert_raised_event import AlertRaisedEvent
from alert.domain.model.events.alert_resolved_event import AlertResolvedEvent
from alert.infrastructure.config.settings import Settings
from alert.infrastructure.logging import configure as configure_logging
from alert.infrastructure.messaging.outbox.outbox_message_publisher import (
    OutboxMessagePublisher,
)
from alert.infrastructure.persistence.repositories.alert_repository_impl import (
    AlertRepositoryImpl,
)
from alert.infrastructure.persistence.session import (
    build_engine,
    build_session_factory,
)
from alert.interfaces.rest import exception_handlers
from alert.interfaces.rest.alerts_controller import router as alerts_router
from alert.interfaces.rest.health_controller import router as health_router
from alert.kernel.domain.event_dispatcher import EventDispatcher


def _build_repository_builder() -> Any:
    def repository_builder(session: Any) -> AlertRepositoryImpl:
        publisher = OutboxMessagePublisher(session)
        raised_handler = AlertRaisedEventHandler(publisher)
        resolved_handler = AlertResolvedEventHandler(publisher)
        dispatcher = EventDispatcher()
        dispatcher.register(AlertRaisedEvent, raised_handler.on_alert_raised)
        dispatcher.register(AlertResolvedEvent, resolved_handler.on_alert_resolved)
        return AlertRepositoryImpl(session, dispatcher)

    return repository_builder


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    repository_builder = _build_repository_builder()

    command_service = AlertApplicationServiceImpl(
        session_factory=session_factory,
        repository_builder=repository_builder,
    )
    query_service = AlertQueryServiceImpl(
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
        title="Alert Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.alert_application_service = command_service
    app.state.alert_query_service = query_service

    exception_handlers.register(app)
    app.include_router(health_router)
    app.include_router(alerts_router)

    return app


app = create_app()
