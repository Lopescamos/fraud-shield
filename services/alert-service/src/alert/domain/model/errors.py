from __future__ import annotations


class InvalidAlertTransition(Exception):
    """Raised when a caller tries to transition an Alert between
    disallowed states (e.g. resolve while still OPEN)."""

    def __init__(self, current: str, attempted: str, reason: str) -> None:
        super().__init__(
            f"Cannot transition Alert from {current} to {attempted}: {reason}"
        )
        self.current = current
        self.attempted = attempted
        self.reason = reason
