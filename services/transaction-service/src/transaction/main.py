from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from transaction.application.internal.commandservices.transaction_command_service_impl import (
    TransactionCommandServiceImpl,
)
from transaction.application.internal.eventhandlers.transaction_registered_event_handler import (
    TransactionRegisteredEventHandler,
)
from transaction.application.internal.queryservices.transaction_query_service_impl import (
    TransactionQueryServiceImpl,
)
from transaction.domain.model.events.transaction_registered_event import (
    TransactionRegisteredEvent,
)
from transaction.infrastructure.config.settings import Settings
from transaction.infrastructure.logging import configure as configure_logging
from transaction.infrastructure.messaging.outbox.outbox_message_publisher import (
    OutboxMessagePublisher,
)
from transaction.infrastructure.persistence.repositories.transaction_repository_impl import (
    TransactionRepositoryImpl,
)
from transaction.infrastructure.persistence.session import (
    build_engine,
    build_session_factory,
)
from transaction.interfaces.rest import exception_handlers
from transaction.interfaces.rest.health_controller import router as health_router
from transaction.interfaces.rest.transactions_controller import (
    router as transactions_router,
)
from transaction.kernel.domain.event_dispatcher import EventDispatcher


def _build_repository_builder() -> Any:
    def repository_builder(session: Any) -> TransactionRepositoryImpl:
        publisher = OutboxMessagePublisher(session)
        handler = TransactionRegisteredEventHandler(publisher)
        dispatcher = EventDispatcher()
        dispatcher.register(
            TransactionRegisteredEvent, handler.on_transaction_registered
        )
        return TransactionRepositoryImpl(session, dispatcher)

    return repository_builder


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    repository_builder = _build_repository_builder()

    command_service = TransactionCommandServiceImpl(
        session_factory=session_factory,
        repository_builder=repository_builder,
    )
    query_service = TransactionQueryServiceImpl(
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
        title="Transaction Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.transaction_command_service = command_service
    app.state.transaction_query_service = query_service

    exception_handlers.register(app)
    app.include_router(health_router)
    app.include_router(transactions_router)

    return app


app = create_app()
