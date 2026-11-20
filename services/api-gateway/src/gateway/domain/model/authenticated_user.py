from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Carried in request.state after the JWT middleware validates the
    token. The gateway uses ``analyst_id`` to enrich downstream requests
    (e.g. the alert PATCH /assign body)."""

    username: str
    analyst_id: UUID
