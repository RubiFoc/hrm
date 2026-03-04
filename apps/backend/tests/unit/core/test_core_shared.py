"""Unit tests for shared core package helpers and compatibility shims."""

from hrm_backend.auth.models.base import Base as AuthBase
from hrm_backend.core.config import CoreSettings
from hrm_backend.core.config import get_settings as get_core_settings
from hrm_backend.core.config.env import normalize_non_empty, read_positive_int_env
from hrm_backend.core.models.base import Base as CoreBase
from hrm_backend.core.utils.time import ttl_until_epoch
from hrm_backend.settings import AppSettings, get_settings


def test_auth_base_reexports_core_base() -> None:
    """Verify auth model base compatibility path points to shared core base class."""
    assert AuthBase is CoreBase


def test_core_settings_shim_reexports_canonical_settings() -> None:
    """Verify core settings shim maps to canonical app-level settings."""
    assert CoreSettings is AppSettings
    assert get_core_settings is get_settings


def test_read_positive_int_env_parses_or_falls_back() -> None:
    """Verify env int helper returns default for invalid values and parsed positive ints."""
    assert read_positive_int_env(None, 10) == 10
    assert read_positive_int_env("abc", 10) == 10
    assert read_positive_int_env("0", 10) == 10
    assert read_positive_int_env("-2", 10) == 10
    assert read_positive_int_env("42", 10) == 42


def test_normalize_non_empty_uses_trimmed_or_fallback() -> None:
    """Verify string normalization helper trims values and falls back for empty inputs."""
    assert normalize_non_empty(None, "fallback") == "fallback"
    assert normalize_non_empty("   ", "fallback") == "fallback"
    assert normalize_non_empty("  value ", "fallback") == "value"


def test_ttl_until_epoch_is_non_negative() -> None:
    """Verify ttl helper never returns negative values."""
    assert ttl_until_epoch(target_epoch=120, now_epoch=100) == 20
    assert ttl_until_epoch(target_epoch=100, now_epoch=100) == 0
    assert ttl_until_epoch(target_epoch=80, now_epoch=100) == 0
