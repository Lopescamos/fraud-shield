from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from transaction.kernel.application.result import Failure

R = TypeVar("R")


def transactional(
    fn: Callable[..., Awaitable[R]],
) -> Callable[..., Awaitable[R]]:
    """
    Open a session on ``self._session_factory``, begin a transaction and
    expose it on ``self._session`` while ``fn`` runs. Rolls back if ``fn``
    returns a ``Failure`` or raises.
    """

    @wraps(fn)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
        async with self._session_factory() as session:
            async with session.begin() as trans:
                self._session = session
                try:
                    result = await fn(self, *args, **kwargs)
                    if isinstance(result, Failure):
                        await trans.rollback()
                    return result
                except BaseException:
                    if trans.is_active:
                        await trans.rollback()
                    raise
                finally:
                    self._session = None

    return wrapper
