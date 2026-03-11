"""Data-access helpers for onboarding checklist template persistence."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from hrm_backend.employee.models.template import OnboardingTemplate, OnboardingTemplateItem
from hrm_backend.employee.schemas.template import OnboardingChecklistTemplateUpsert


class OnboardingTemplateDAO:
    """Persist and query onboarding checklist templates and their items."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session.

        Args:
            session: Active request or job session.
        """
        self._session = session

    def list_templates(self, *, active_only: bool = False) -> list[OnboardingTemplate]:
        """List onboarding templates in deterministic order.

        Args:
            active_only: When `True`, return only active templates.

        Returns:
            list[OnboardingTemplate]: Ordered template entities.
        """
        query = self._session.query(OnboardingTemplate)
        if active_only:
            query = query.filter(OnboardingTemplate.is_active.is_(True))
        return list(
            query.order_by(
                OnboardingTemplate.is_active.desc(),
                OnboardingTemplate.created_at.asc(),
                OnboardingTemplate.template_id.asc(),
            ).all()
        )

    def get_by_id(self, template_id: str) -> OnboardingTemplate | None:
        """Load one onboarding template by identifier."""
        return self._session.get(OnboardingTemplate, template_id)

    def get_by_name(self, name: str) -> OnboardingTemplate | None:
        """Load one onboarding template by unique name."""
        return (
            self._session.query(OnboardingTemplate)
            .filter(OnboardingTemplate.name == name)
            .first()
        )

    def get_active_template(self) -> OnboardingTemplate | None:
        """Load the current active onboarding template, if one exists."""
        return (
            self._session.query(OnboardingTemplate)
            .filter(OnboardingTemplate.is_active.is_(True))
            .order_by(
                OnboardingTemplate.created_at.asc(),
                OnboardingTemplate.template_id.asc(),
            )
            .first()
        )

    def list_items_for_template_ids(
        self,
        template_ids: Sequence[str],
    ) -> list[OnboardingTemplateItem]:
        """Load checklist items for one or more template identifiers."""
        if not template_ids:
            return []
        return list(
            self._session.query(OnboardingTemplateItem)
            .filter(OnboardingTemplateItem.template_id.in_(list(template_ids)))
            .order_by(
                OnboardingTemplateItem.template_id.asc(),
                OnboardingTemplateItem.sort_order.asc(),
                OnboardingTemplateItem.template_item_id.asc(),
            )
            .all()
        )

    def create_template(
        self,
        *,
        payload: OnboardingChecklistTemplateUpsert,
        created_by_staff_id: str,
        commit: bool = True,
    ) -> OnboardingTemplate:
        """Insert one onboarding checklist template row."""
        entity = OnboardingTemplate(
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            created_by_staff_id=created_by_staff_id,
        )
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def update_template(
        self,
        *,
        entity: OnboardingTemplate,
        payload: OnboardingChecklistTemplateUpsert,
        commit: bool = True,
    ) -> OnboardingTemplate:
        """Replace editable onboarding template fields."""
        entity.name = payload.name
        entity.description = payload.description
        entity.is_active = payload.is_active
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def replace_items(
        self,
        *,
        template_id: str,
        payload: OnboardingChecklistTemplateUpsert,
        commit: bool = True,
    ) -> list[OnboardingTemplateItem]:
        """Replace all checklist items for one template."""
        self._session.query(OnboardingTemplateItem).filter(
            OnboardingTemplateItem.template_id == template_id
        ).delete(synchronize_session=False)

        entities = [
            OnboardingTemplateItem(
                template_id=template_id,
                code=item.code,
                title=item.title,
                description=item.description,
                sort_order=item.sort_order,
                is_required=item.is_required,
            )
            for item in payload.items
        ]
        for entity in entities:
            self._session.add(entity)

        if commit:
            self._session.commit()
            for entity in entities:
                self._session.refresh(entity)
            return entities

        self._session.flush()
        return entities

    def deactivate_other_templates(
        self,
        *,
        active_template_id: str,
        commit: bool = True,
    ) -> None:
        """Clear active flag from every template except the selected one."""
        (
            self._session.query(OnboardingTemplate)
            .filter(
                OnboardingTemplate.template_id != active_template_id,
                OnboardingTemplate.is_active.is_(True),
            )
            .update({OnboardingTemplate.is_active: False}, synchronize_session=False)
        )
        if commit:
            self._session.commit()
        else:
            self._session.flush()
