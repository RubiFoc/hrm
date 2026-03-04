"""Compatibility shim for auth settings.

Canonical settings module: `hrm_backend.settings`.
"""

from hrm_backend.settings import AppSettings, get_settings

# Temporary compatibility aliases for legacy auth imports.
AuthSettings = AppSettings
get_auth_settings = get_settings

__all__ = ["AuthSettings", "get_auth_settings"]
