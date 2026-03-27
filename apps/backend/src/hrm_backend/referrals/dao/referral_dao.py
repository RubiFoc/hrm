"""DAO helpers for employee referral persistence."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from hrm_backend.referrals.models.referral import EmployeeReferral
from hrm_backend.referrals.schemas.referral import ReferralCreate


class EmployeeReferralDAO:
    """Data-access helper for employee referral records."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def get_by_id(self, referral_id: str) -> EmployeeReferral | None:
        """Fetch referral by identifier.

        Args:
            referral_id: Referral identifier.

        Returns:
            EmployeeReferral | None: Matched referral row or `None`.
        """
        return self._session.get(EmployeeReferral, referral_id)

    def get_by_vacancy_and_email(
        self,
        *,
        vacancy_id: str,
        email: str,
    ) -> EmployeeReferral | None:
        """Fetch referral by vacancy and normalized email.

        Args:
            vacancy_id: Vacancy identifier.
            email: Normalized email value.

        Returns:
            EmployeeReferral | None: Matched referral row or `None`.
        """
        return (
            self._session.query(EmployeeReferral)
            .filter(
                EmployeeReferral.vacancy_id == vacancy_id,
                EmployeeReferral.email == email,
            )
            .first()
        )

    def create_referral(
        self,
        *,
        payload: ReferralCreate,
        commit: bool = True,
    ) -> EmployeeReferral:
        """Insert one referral row.

        Args:
            payload: Typed referral creation payload.
            commit: When `True`, commit immediately; otherwise only flush.

        Returns:
            EmployeeReferral: Persisted referral entity.
        """
        entity = EmployeeReferral(
            vacancy_id=str(payload.vacancy_id),
            candidate_id=str(payload.candidate_id) if payload.candidate_id else None,
            referrer_employee_id=str(payload.referrer_employee_id),
            bonus_owner_employee_id=str(payload.bonus_owner_employee_id),
            full_name=payload.full_name,
            phone=payload.phone,
            email=payload.email,
            cv_document_id=str(payload.cv_document_id) if payload.cv_document_id else None,
            consent_confirmed_at=payload.consent_confirmed_at,
            submitted_at=payload.submitted_at,
        )
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def list_referrals(
        self,
        *,
        vacancy_ids: list[str] | None,
        limit: int,
        offset: int,
    ) -> list[EmployeeReferral]:
        """List referral rows with optional vacancy scoping.

        Args:
            vacancy_ids: Optional vacancy identifiers to scope the query.
            limit: Maximum number of rows to return.
            offset: Row offset for pagination.

        Returns:
            list[EmployeeReferral]: Ordered referral rows.
        """
        query = self._session.query(EmployeeReferral)
        if vacancy_ids is not None:
            if not vacancy_ids:
                return []
            query = query.filter(EmployeeReferral.vacancy_id.in_(vacancy_ids))

        return list(
            query.order_by(
                EmployeeReferral.submitted_at.desc(),
                EmployeeReferral.referral_id.asc(),
            )
            .limit(limit)
            .offset(offset)
            .all()
        )

    def count_referrals(self, *, vacancy_ids: list[str] | None) -> int:
        """Count referrals with optional vacancy scoping.

        Args:
            vacancy_ids: Optional vacancy identifiers to scope the count.

        Returns:
            int: Total referral count.
        """
        query = self._session.query(func.count(EmployeeReferral.referral_id))
        if vacancy_ids is not None:
            if not vacancy_ids:
                return 0
            query = query.filter(EmployeeReferral.vacancy_id.in_(vacancy_ids))
        return int(query.scalar() or 0)
