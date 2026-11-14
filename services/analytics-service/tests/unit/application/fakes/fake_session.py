from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any


class FakeSession:
    def __init__(self) -> None:
        self.begin_count = 0

    @asynccontextmanager
    async def begin(self):
        self.begin_count += 1
        yield None

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None


def session_factory_with(session: FakeSession) -> Any:
    def factory() -> FakeSession:
        return session

    return factory
