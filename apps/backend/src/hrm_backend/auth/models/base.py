"""Compatibility re-export for auth domain SQLAlchemy base model.

Use `hrm_backend.core.models.base.Base` as the stable import path for all new
domain packages.
"""

from hrm_backend.core.models.base import Base

__all__ = ["Base"]
