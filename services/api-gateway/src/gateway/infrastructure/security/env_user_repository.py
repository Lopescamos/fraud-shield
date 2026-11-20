from __future__ import annotations

from uuid import UUID

from gateway.application.auth_service import StoredUser, UserRepository


class EnvUserRepository(UserRepository):
    """Loads users from the CSV env var ``GATEWAY_USERS``, with entries
    shaped ``username:bcrypt_hash:analyst_uuid``. In production this gets
    replaced by an IdP; the shape of the port stays the same."""

    def __init__(self, raw_csv: str) -> None:
        self._by_username: dict[str, StoredUser] = {}
        for entry in raw_csv.split(","):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split(":", 2)
            if len(parts) != 3:
                continue
            username, hashed, analyst_id = parts
            self._by_username[username] = StoredUser(
                username=username,
                hashed_password=hashed,
                analyst_id=UUID(analyst_id),
            )

    def find(self, username: str) -> StoredUser | None:
        return self._by_username.get(username)
