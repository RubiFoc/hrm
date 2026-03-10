"""Alembic environment configuration for backend migrations."""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from hrm_backend.audit.models.event import AuditEvent  # noqa: F401
from hrm_backend.auth.models.employee_registration_key import EmployeeRegistrationKey  # noqa: F401
from hrm_backend.auth.models.staff_account import StaffAccount  # noqa: F401
from hrm_backend.candidates.models.document import CandidateDocument  # noqa: F401
from hrm_backend.candidates.models.parsing_job import CVParsingJob  # noqa: F401
from hrm_backend.candidates.models.profile import CandidateProfile  # noqa: F401
from hrm_backend.core.models.base import Base
from hrm_backend.interviews.models.feedback import InterviewFeedback  # noqa: F401
from hrm_backend.interviews.models.interview import Interview  # noqa: F401
from hrm_backend.interviews.models.calendar_binding import InterviewCalendarBinding  # noqa: F401
from hrm_backend.scoring.models.score_artifact import MatchScoreArtifact  # noqa: F401
from hrm_backend.scoring.models.scoring_job import MatchScoringJob  # noqa: F401
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition  # noqa: F401
from hrm_backend.vacancies.models.vacancy import Vacancy  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def _database_url() -> str:
    """Resolve database URL from environment or Alembic config.

    Returns:
        str: SQLAlchemy database URL string.
    """
    return os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
