from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any


class FakeTransaction:
    def __init__(self) -> None:
        self.is_active = True
        self.committed = False
        self.rolled_back = False

    async def rollback(self) -> None:
        self.is_active = False
        self.rolled_back = True


class FakeSession:
    def __init__(self) -> None:
        self.trans = FakeTransaction()

    @asynccontextmanager
    async def begin(self):
        yield self.trans
        self.trans.committed = True

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None


def session_factory_with(session: FakeSession) -> Any:
    def factory() -> FakeSession:
        return session

    return factory


def repo_builder(repo) -> Any:
    def builder(_session: Any):
        return repo

    return builder
