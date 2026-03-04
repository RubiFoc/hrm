"""Password hashing and policy validation for staff authentication."""

from __future__ import annotations

import re

from fastapi import HTTPException, status
from passlib.hash import argon2


class PasswordService:
    """Encapsulates Argon2id hashing and password policy checks."""

    def validate_policy(self, password: str) -> None:
        """Validate baseline password policy and raise HTTP 422 on violations."""
        if len(password) < 12:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Password must be at least 12 characters",
            )
        if re.search(r"[A-Z]", password) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Password must include uppercase letter",
            )
        if re.search(r"[a-z]", password) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Password must include lowercase letter",
            )
        if re.search(r"\d", password) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Password must include digit",
            )
        if re.search(r"[^A-Za-z0-9]", password) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Password must include special character",
            )

    def hash_password(self, password: str) -> str:
        """Validate and hash password with Argon2id."""
        self.validate_policy(password)
        return argon2.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify plaintext password against Argon2id hash."""
        return bool(argon2.verify(password, password_hash))
