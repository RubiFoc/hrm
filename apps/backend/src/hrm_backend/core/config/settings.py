"""Compatibility shim for shared settings.

Canonical settings module: `hrm_backend.settings`.
"""

from hrm_backend.settings import AppSettings, get_settings

# Temporary compatibility alias for existing imports.
CoreSettings = AppSettings

__all__ = ["AppSettings", "CoreSettings", "get_settings"]
