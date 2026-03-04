"""Compatibility shim for candidate storage adapters.

Infrastructure adapters are now located in `hrm_backend.candidates.infra.minio`.
"""

from hrm_backend.candidates.infra.minio.storage import CandidateStorage, MinioCandidateStorage

__all__ = ["CandidateStorage", "MinioCandidateStorage"]
