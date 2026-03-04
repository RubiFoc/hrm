"""Shared utility helpers used across backend domains."""

from hrm_backend.core.utils.time import ttl_until_epoch, utc_now_epoch

__all__ = ["utc_now_epoch", "ttl_until_epoch"]
