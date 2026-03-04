"""MinIO adapters for candidate domain."""

from hrm_backend.candidates.infra.minio.storage import CandidateStorage, MinioCandidateStorage

__all__ = ["CandidateStorage", "MinioCandidateStorage"]
