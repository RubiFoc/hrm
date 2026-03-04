"""Manual CLI bootstrap for the first admin account."""

from __future__ import annotations

import argparse
import sys

from fastapi import HTTPException

from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.infra.security.password_service import PasswordService
from hrm_backend.core.db.session import get_session_factory
from hrm_backend.settings import get_settings


def main(argv: list[str] | None = None) -> int:
    """Create first admin account in database via CLI arguments."""
    parser = argparse.ArgumentParser(description="Create bootstrap admin account")
    parser.add_argument("--login", required=True, help="Admin login")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    args = parser.parse_args(argv)

    login = args.login.strip().lower()
    email = args.email.strip().lower()

    settings = get_settings()
    session_factory = get_session_factory(settings.database_url)
    session = session_factory()
    try:
        dao = StaffAccountDAO(session=session)
        if dao.get_by_login(login) is not None:
            print("Admin bootstrap aborted: login already exists", file=sys.stderr)
            return 1
        if dao.get_by_email(email) is not None:
            print("Admin bootstrap aborted: email already exists", file=sys.stderr)
            return 1

        password_hash = PasswordService().hash_password(args.password)
        account = dao.create_account(
            login=login,
            email=email,
            password_hash=password_hash,
            role="admin",
            is_active=True,
        )
        print(f"Created admin account staff_id={account.staff_id}")
        return 0
    except HTTPException as exc:
        print(f"Admin bootstrap failed: {exc.detail}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
