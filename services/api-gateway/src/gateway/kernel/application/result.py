from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Success(Generic[T]):
    value: T


@dataclass(frozen=True, slots=True)
class Failure(Generic[E]):
    error: E


Result = Success[T] | Failure[E]


@dataclass(frozen=True, slots=True)
class ApplicationError:
    code: str
    title: str
    detail: str

    @staticmethod
    def unauthorized(detail: str) -> ApplicationError:
        return ApplicationError(
            code="unauthorized", title="Authentication failed", detail=detail
        )

    @staticmethod
    def forbidden(detail: str) -> ApplicationError:
        return ApplicationError(code="forbidden", title="Forbidden", detail=detail)

    @staticmethod
    def validation_error(field: str, detail: str) -> ApplicationError:
        return ApplicationError(
            code="validation_error",
            title=f"Validation failed for '{field}'",
            detail=detail,
        )

    @staticmethod
    def upstream_error(service: str, detail: str) -> ApplicationError:
        return ApplicationError(
            code="upstream_error",
            title=f"Upstream service '{service}' failed",
            detail=detail,
        )
