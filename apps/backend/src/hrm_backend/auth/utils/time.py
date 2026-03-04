"""Compatibility re-export for auth time helpers.

Use `hrm_backend.core.utils.time` as the stable source for shared time helpers.
"""

from hrm_backend.core.utils.time import ttl_until_epoch, utc_now_epoch

__all__ = ["utc_now_epoch", "ttl_until_epoch"]
