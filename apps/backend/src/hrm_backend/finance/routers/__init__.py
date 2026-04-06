"""Router exports for the finance domain package."""

from hrm_backend.finance.routers.compensation_v1 import router as compensation_router
from hrm_backend.finance.routers.v1 import router as finance_router

__all__ = ["compensation_router", "finance_router"]
