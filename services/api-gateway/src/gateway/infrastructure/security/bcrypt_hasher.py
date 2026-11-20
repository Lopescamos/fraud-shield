from __future__ import annotations

import bcrypt

from gateway.application.auth_service import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    def verify(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False

    @staticmethod
    def hash(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
