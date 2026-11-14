from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from analytics.application.internal.commandservices.projection_application_service_impl import (
    ProjectionApplicationServiceImpl,
)
from analytics.application.internal.queryservices.query_application_service_impl import (
    QueryApplicationServiceImpl,
)
from analytics.infrastructure.config.settings import Settings
from analytics.infrastructure.logging import configure as configure_logging
from analytics.infrastructure.persistence.repositories.analytics_projection_repository_impl import (
    AnalyticsProjectionRepositoryImpl,
)
from analytics.infrastructure.persistence.repositories.analytics_read_repository_impl import (
    AnalyticsReadRepositoryImpl,
)
from analytics.infrastructure.persistence.repositories.processed_event_store_impl import (
    ProcessedEventStoreImpl,
)
from analytics.infrastructure.persistence.session import (
    build_engine,
    build_session_factory,
)
from analytics.interfaces.rest import exception_handlers
from analytics.interfaces.rest.analytics_controller import router as analytics_router
from analytics.interfaces.rest.health_controller import router as health_router
from analytics.interfaces.rest.security import api_key


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)

    projection_service = ProjectionApplicationServiceImpl(
        session_factory=session_factory,
        projection_builder=lambda session: AnalyticsProjectionRepositoryImpl(session),
        store_builder=lambda session: ProcessedEventStoreImpl(session),
    )
    query_service = QueryApplicationServiceImpl(
        session_factory=session_factory,
        read_builder=lambda session: AnalyticsReadRepositoryImpl(session),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="Analytics Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.projection_application_service = projection_service
    app.state.query_application_service = query_service

    api_key.register(app, settings.api_key_set())
    exception_handlers.register(app)
    app.include_router(health_router)
    app.include_router(analytics_router)

    return app


app = create_app()


def _get_projection_service(app: FastAPI) -> Any:
    """Convenience accessor used by the Kafka consumer when wired."""
    return app.state.projection_application_service
