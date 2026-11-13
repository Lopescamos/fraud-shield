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
    def validation_error(field: str, detail: str) -> "ApplicationError":
        return ApplicationError(
            code="validation_error",
            title=f"Validation failed for '{field}'",
            detail=detail,
        )

    @staticmethod
    def not_found(aggregate: str, id_: str) -> "ApplicationError":
        return ApplicationError(
            code="not_found",
            title=f"{aggregate} not found",
            detail=f"{aggregate} with id '{id_}' does not exist",
        )

    @staticmethod
    def business_rule_violation(aggregate: str, rule: str) -> "ApplicationError":
        return ApplicationError(
            code="business_rule_violation",
            title=f"{aggregate} business rule violation",
            detail=rule,
        )

    @staticmethod
    def conflict(aggregate: str, detail: str) -> "ApplicationError":
        return ApplicationError(
            code="conflict",
            title=f"{aggregate} conflict",
            detail=detail,
        )

    @staticmethod
    def unexpected(operation: str, detail: str) -> "ApplicationError":
        return ApplicationError(
            code="unexpected",
            title=f"Unexpected error while {operation}",
            detail=detail,
        )
