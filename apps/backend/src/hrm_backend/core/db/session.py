"""SQLAlchemy session factory and dependency helpers."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hrm_backend.settings import AppSettings, get_settings


@lru_cache(maxsize=4)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    """Build and cache SQLAlchemy session factory by database URL.

    Args:
        database_url: SQLAlchemy database URL.

    Returns:
        sessionmaker[Session]: Session factory bound to requested database URL.
    """
    engine = create_engine(database_url, future=True, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db_session(
    settings: Annotated[AppSettings, Depends(get_settings)],
) -> Generator[Session, None, None]:
    """Yield managed SQLAlchemy session for request/background scopes.

    Args:
        settings: Application runtime settings.

    Yields:
        Session: SQLAlchemy session instance.
    """
    factory = _session_factory(settings.database_url)
    session = factory()
    try:
        yield session
    finally:
        session.close()
